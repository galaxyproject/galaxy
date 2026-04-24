"""Monitor for history audit table changes.

Detects history changes via PostgreSQL LISTEN/NOTIFY (instant) or by polling
the history_audit table (SQLite fallback). Dispatches SSE events to connected
users via Kombu control tasks.

Only active when ``enable_sse_history_updates`` is True in the Galaxy config.
"""

import logging
import select
import threading
import time
from collections import (
    defaultdict,
    OrderedDict,
)
from collections.abc import Iterator
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Any,
    Optional,
)

from sqlalchemy import select as sa_select
from sqlalchemy.engine import Engine

from galaxy.config import GalaxyAppConfiguration
from galaxy.managers.sse_dispatch import SSEEventDispatcher
from galaxy.model import (
    GalaxySessionToHistoryAssociation,
    History,
    HistoryAudit,
)
from galaxy.model.mapping import GalaxyModelMapping

log = logging.getLogger(__name__)

CHANNEL_NAME = "galaxy_history_update"
OWNER_CACHE_MAX = 10_000
DEBOUNCE_SECONDS = 0.2


class _PgListenAdapter:
    """Thin DBAPI-level adapter for PostgreSQL LISTEN/NOTIFY.

    Hides the receiving-API differences between psycopg2 (``conn.poll()`` +
    ``conn.notifies`` list, driven by ``select.select``) and psycopg3
    (``conn.notifies(timeout=...)`` generator). The SA URL is used to inherit
    DSN / SSL / auth config, but the connection itself is opened directly with
    the DBAPI driver so it stays outside the SA pool — LISTEN connections must
    live for the lifetime of the monitor and never be returned to the pool.
    """

    def __init__(self, engine: Engine) -> None:
        # Strip the SA ``+driver`` suffix so the raw DBAPI libraries accept the URL.
        dsn = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
        driver = engine.dialect.driver
        if driver == "psycopg":
            import psycopg  # conditional: psycopg3 driver

            self._conn: Any = psycopg.connect(dsn, autocommit=True)
            self.driver = "psycopg3"
        else:
            import psycopg2  # conditional: psycopg2 driver

            self._conn = psycopg2.connect(dsn)
            self._conn.autocommit = True  # same effect as set_isolation_level(AUTOCOMMIT)
            self.driver = "psycopg2"

    def listen(self, channel: str) -> None:
        with self._conn.cursor() as cursor:
            cursor.execute(f"LISTEN {channel};")

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            log.debug("Error closing LISTEN connection", exc_info=True)

    def poll(self, timeout: float) -> Iterator[str]:
        """Block up to ``timeout`` seconds and yield notification payloads.

        Returns an empty iterator on timeout so callers can uniformly treat
        "nothing received in this tick" regardless of driver.
        """
        if self.driver == "psycopg3":
            # psycopg3: notifies() is a blocking generator bounded by ``timeout``.
            yield from (n.payload for n in self._conn.notifies(timeout=timeout))
            return
        # psycopg2: block on the socket via select(), then drain notifies list.
        if select.select([self._conn], [], [], timeout) == ([], [], []):
            return
        self._conn.poll()
        while self._conn.notifies:
            yield self._conn.notifies.pop(0).payload


class HistoryAuditMonitor:
    """Background thread that monitors history_audit for changes and dispatches SSE events.

    On PostgreSQL: uses LISTEN/NOTIFY for instant notification.
    On SQLite: polls history_audit table at a configurable interval.
    """

    def __init__(
        self,
        config: GalaxyAppConfiguration,
        model: GalaxyModelMapping,
        sse_dispatcher: SSEEventDispatcher,
    ) -> None:
        self._config = config
        self._model = model
        self._dispatcher = sse_dispatcher
        self.poll_interval: int = config.history_audit_monitor_poll_interval
        self._is_postgres: bool = "postgres" in model.engine.name
        self._exit = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._active = False
        # Bounded LRU cache: history_id -> (user_id, session_ids), refreshed on miss.
        # For registered-owned histories: (user_id, ()); for anonymous histories:
        # (None, (session_id, ...)) — a history can be associated with multiple
        # sessions via GalaxySessionToHistoryAssociation.
        self._history_owner_cache: OrderedDict[int, tuple[Optional[int], tuple[int, ...]]] = OrderedDict()

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._exit.clear()  # allow restart after a previous shutdown
        target = self._listen_postgres if self._is_postgres else self._poll_audit_table
        self._thread = threading.Thread(
            target=target,
            name="history_audit_monitor",
            daemon=True,
        )
        self._thread.start()
        log.info(
            "HistoryAuditMonitor started (mode=%s, interval=%ds)",
            "pg_listen" if self._is_postgres else "poll",
            self.poll_interval,
        )

    def shutdown(self) -> None:
        if not self._active:
            return
        self._active = False
        self._exit.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None
        log.info("HistoryAuditMonitor stopped")

    def on_role_change(self, is_leader: bool) -> None:
        """Heartbeat callback: start/stop the monitor as this process's election state changes."""
        if is_leader:
            self.start()
        else:
            self.shutdown()

    # --- PostgreSQL LISTEN/NOTIFY mode ---

    def _listen_postgres(self) -> None:
        """LISTEN for history update notifications.

        Works against both psycopg2 and psycopg3 — whichever driver the SA
        engine was built with. Falls back to the SQLite polling path if the
        DBAPI driver can't be imported or the initial LISTEN fails.
        """
        try:
            adapter = _PgListenAdapter(self._model.engine)
            adapter.listen(CHANNEL_NAME)
        except Exception:
            log.warning(
                "Failed to establish PostgreSQL LISTEN connection, falling back to polling",
                exc_info=True,
            )
            self._poll_audit_table()
            return

        log.debug("LISTEN %s established (driver=%s)", CHANNEL_NAME, adapter.driver)
        pending: dict[int, float] = {}  # history_id -> first_seen_time

        try:
            while not self._exit.is_set():
                received_any = False
                for payload in adapter.poll(self.poll_interval):
                    received_any = True
                    try:
                        history_id = int(payload)
                    except (ValueError, TypeError):
                        continue
                    pending.setdefault(history_id, time.monotonic())

                if not received_any:
                    # Timeout — flush anything that's been pending since last tick
                    if pending:
                        self._dispatch_history_updates(set(pending.keys()))
                        pending.clear()
                    continue

                # Debounce: dispatch events that have been pending long enough
                now = time.monotonic()
                ready = {hid for hid, ts in pending.items() if now - ts >= DEBOUNCE_SECONDS}
                if ready:
                    self._dispatch_history_updates(ready)
                    for hid in ready:
                        del pending[hid]
        except Exception:
            log.exception("HistoryAuditMonitor LISTEN loop error")
        finally:
            adapter.close()

    # --- SQLite polling fallback ---

    def _poll_audit_table(self) -> None:
        """Poll history_audit for recent changes."""
        last_check = datetime.utcnow() - timedelta(seconds=self.poll_interval)

        while not self._exit.is_set():
            try:
                check_time = datetime.utcnow()
                stmt = (
                    sa_select(HistoryAudit.history_id)
                    .where(HistoryAudit.update_time > last_check)
                    .group_by(HistoryAudit.history_id)
                )
                with self._model.new_session() as session:
                    changed_ids = set(session.scalars(stmt).all())

                if changed_ids:
                    self._dispatch_history_updates(changed_ids)

                last_check = check_time
            except Exception:
                log.exception("HistoryAuditMonitor poll error")

            self._exit.wait(self.poll_interval)

    # --- Common dispatch logic ---

    def _dispatch_history_updates(self, history_ids: set[int]) -> None:
        """Map history_ids to user_ids / session_ids and send Kombu control task.

        Raw integer history IDs are sent across the control queue; encoding is
        deferred to the ``history_update`` task handler on the receiving side,
        keeping this manager free of presentation concerns.
        """
        # Resolve owners for unknown history_ids
        unknown = history_ids - self._history_owner_cache.keys()
        if unknown:
            self._refresh_owner_cache(unknown)

        user_updates: dict[str, list[int]] = defaultdict(list)
        session_updates: dict[str, list[int]] = defaultdict(list)
        for history_id in history_ids:
            entry = self._history_owner_cache.get(history_id)
            if entry is None:
                continue
            user_id, session_ids = entry
            if user_id is not None:
                user_updates[str(user_id)].append(history_id)
            else:
                for session_id in session_ids:
                    session_updates[str(session_id)].append(history_id)

        if not user_updates and not session_updates:
            return

        self._dispatcher.history_update(
            user_updates=dict(user_updates),
            session_updates=dict(session_updates) if session_updates else None,
        )

    def _refresh_owner_cache(self, history_ids: set[int]) -> None:
        """Look up ownership for given history_ids and update the bounded cache.

        Registered-owned histories resolve with just ``History.user_id``. For
        histories where ``user_id IS NULL`` we additionally fetch associated
        ``galaxy_session.id`` values from ``GalaxySessionToHistoryAssociation``
        so the anonymous SSE dispatch path can target the right browser.
        """
        try:
            with self._model.new_session() as session:
                stmt = sa_select(History.id, History.user_id).where(History.id.in_(history_ids))
                anon_history_ids: set[int] = set()
                for row in session.execute(stmt):
                    hid, uid = row[0], row[1]
                    self._history_owner_cache[hid] = (uid, ())
                    self._history_owner_cache.move_to_end(hid)
                    if uid is None:
                        anon_history_ids.add(hid)

                if anon_history_ids:
                    assoc_stmt = sa_select(
                        GalaxySessionToHistoryAssociation.history_id,
                        GalaxySessionToHistoryAssociation.session_id,
                    ).where(GalaxySessionToHistoryAssociation.history_id.in_(anon_history_ids))
                    sessions_by_history: dict[int, list[int]] = defaultdict(list)
                    for row in session.execute(assoc_stmt):
                        hid, sid = row[0], row[1]
                        if sid is not None:
                            sessions_by_history[hid].append(sid)
                    for hid, sids in sessions_by_history.items():
                        self._history_owner_cache[hid] = (None, tuple(sids))

            while len(self._history_owner_cache) > OWNER_CACHE_MAX:
                self._history_owner_cache.popitem(last=False)
        except Exception:
            log.debug("Failed to refresh history owner cache", exc_info=True)

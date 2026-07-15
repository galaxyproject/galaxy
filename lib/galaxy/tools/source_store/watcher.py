"""Polling watcher reacting to externally-updated tool source stores.

A store published outside this Galaxy process — the CVMFS model, where a
publisher repopulates the sqlite bundle in the same transaction that ships
new tools — changes without any local filesystem event (inotify does not
fire on CVMFS). Polling each store's freshness probe is the only reliable
signal, and it is cheap: one probe per store per tick.

The watcher itself is deliberately dumb: it detects token transitions and
hands the changed store names to ``on_change``. Reload mechanics —
disposing engines so new connections see the new CVMFS snapshot, index
reload, panel refresh, whoosh rebuild — belong to the callback owner
(``LazyToolBox``).
"""

import logging
import threading
from collections.abc import Callable

from .interface import ToolSourceStore

log = logging.getLogger(__name__)


class ToolSourceStoreWatcher:
    """Poll member stores' freshness probes; report token transitions.

    Args:
        members: ``(name, store)`` pairs to watch. Callers pass read-only
            stores with a probe — writable stores change through this
            process's own populate paths, which broadcast their own
            reloads.
        interval: Seconds between polls.
        on_change: Called from the watcher thread with the names whose
            token changed since the previous poll.
    """

    def __init__(
        self,
        members: list[tuple[str, ToolSourceStore]],
        interval: float,
        on_change: Callable[[list[str]], None],
    ) -> None:
        self._members = members
        self._interval = interval
        self._on_change = on_change
        self._last_token: dict[str, str] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="ToolSourceStoreWatcher", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self.check()
            except Exception:
                log.exception("Tool source store freshness poll failed")

    def check(self) -> list[str]:
        """One poll tick. Returns the store names whose token transitioned.

        The first sighting of a store's token only records the baseline —
        comparing against the *persisted* index token instead would re-fire
        forever when a store is stale for reasons a reload can't fix (e.g.
        the publisher hasn't repopulated yet).
        """
        changed: list[str] = []
        for name, store in self._members:
            token = store.compute_freshness_token()
            if token is None:
                # Probe failure; the store already logged it.
                continue
            previous = self._last_token.get(name)
            self._last_token[name] = token
            if previous is not None and token != previous:
                log.info("Tool source store %r freshness token changed (%s -> %s)", name, previous, token)
                changed.append(name)
        if changed:
            self._on_change(changed)
        return changed

    def shutdown(self) -> None:
        self._stop.set()

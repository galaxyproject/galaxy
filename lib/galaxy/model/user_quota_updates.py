"""Collect the users whose storage usage or quota a transaction changes, and announce them once it commits.

Code that changes a user's usage or the quotas that apply to them calls :func:`queue_user_quota_update`
on the session it writes with. :func:`send_user_quota_updates_on_commit`, installed once by the app,
hands what was queued to a sender after each commit, so browsers only refetch the usage once the
change is in the database. A rollback discards it. :class:`UserQuotaUpdateBatcher` merges what the
commits of a process hand over and sends it at most once per interval, so a workflow finishing many
jobs sends a few messages instead of one per job.
"""

import logging
import threading
from collections.abc import (
    Callable,
    Iterable,
)
from dataclasses import (
    dataclass,
    field,
)

from sqlalchemy import event
from sqlalchemy.orm import (
    scoped_session,
    Session,
)

log = logging.getLogger(__name__)

_INFO_KEY = "galaxy_user_quota_updates"
_ENABLED_KEY = "galaxy_user_quota_updates_enabled"


@dataclass
class UserQuotaUpdates:
    """The users to tell, and whether to tell everyone, as when a default quota changes."""

    user_ids: set[int] = field(default_factory=set)
    broadcast: bool = False

    def merge(self, other: "UserQuotaUpdates") -> None:
        self.user_ids.update(other.user_ids)
        self.broadcast = self.broadcast or other.broadcast


def user_quota_updates_enabled(session: Session | scoped_session[Session]) -> bool:
    """Whether updates queued in ``session`` are sent, so callers can skip queries only needed to queue them."""
    return bool(session.info.get(_ENABLED_KEY))


def queue_user_quota_update(
    session: Session | scoped_session[Session], user_ids: Iterable[int] = (), broadcast: bool = False
) -> None:
    """Announce, after the session's next commit, that these users' storage usage or quota changed."""
    if not user_quota_updates_enabled(session):
        return
    user_ids = set(user_ids)
    if not user_ids and not broadcast:
        return
    session.info.setdefault(_INFO_KEY, UserQuotaUpdates()).merge(UserQuotaUpdates(user_ids, broadcast))


def send_user_quota_updates_on_commit(
    session: scoped_session[Session], send: Callable[[UserQuotaUpdates], None]
) -> None:
    """Enable queueing in ``session`` and pass what is queued to ``send`` after each commit.

    This applies to every session the scoped session's factory creates. Without it, queueing does nothing.
    """
    session.session_factory.kw.setdefault("info", {})[_ENABLED_KEY] = True
    if session.registry.has():
        session.info[_ENABLED_KEY] = True

    def after_commit(session: Session) -> None:
        updates = session.info.pop(_INFO_KEY, None)
        if updates is None:
            return
        try:
            send(updates)
        except Exception:
            # The change is committed already, so failing to announce it must not fail the request
            log.exception("Failed to send user quota updates")

    def after_rollback(session: Session) -> None:
        session.info.pop(_INFO_KEY, None)

    event.listen(session, "after_commit", after_commit)
    event.listen(session, "after_rollback", after_rollback)


class UserQuotaUpdateBatcher:
    """Merges the updates added to it and sends them together, ``interval`` seconds after the first one.

    Sending happens on a timer thread, so the committing thread, e.g. a job handler, never waits for it.
    """

    def __init__(self, send: Callable[[UserQuotaUpdates], None], interval: float = 1.0) -> None:
        self._send = send
        self._interval = interval
        self._lock = threading.Lock()
        self._pending: UserQuotaUpdates | None = None
        self._timer: threading.Timer | None = None

    def add(self, updates: UserQuotaUpdates) -> None:
        with self._lock:
            if self._pending is None:
                self._pending = UserQuotaUpdates()
            self._pending.merge(updates)
            if self._timer is None:
                self._timer = threading.Timer(self._interval, self.flush)
                self._timer.daemon = True
                self._timer.start()

    def flush(self) -> None:
        """Send what is pending now, e.g. on shutdown."""
        with self._lock:
            pending, self._pending = self._pending, None
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        if pending is None:
            return
        try:
            self._send(pending)
        except Exception:
            log.exception("Failed to send user quota updates")

"""Collect the users whose storage usage or quota a transaction changes, and announce them once it commits.

Code that changes a user's usage or the quotas that apply to them calls :func:`queue_user_quota_update`
on the session it writes with. :func:`send_user_quota_updates_on_commit`, installed once by the app,
hands what was queued to a sender after each commit, so browsers only refetch the usage once the
change is in the database. A rollback discards it.
"""

import logging
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


@dataclass
class UserQuotaUpdates:
    """The users to tell, and whether to tell everyone, as when a default quota changes."""

    user_ids: set[int] = field(default_factory=set)
    broadcast: bool = False


def queue_user_quota_update(
    session: Session | scoped_session[Session], user_ids: Iterable[int] = (), broadcast: bool = False
) -> None:
    """Announce, after the session's next commit, that these users' storage usage or quota changed."""
    user_ids = set(user_ids)
    if not user_ids and not broadcast:
        return
    updates = session.info.setdefault(_INFO_KEY, UserQuotaUpdates())
    updates.user_ids.update(user_ids)
    updates.broadcast = updates.broadcast or broadcast


def send_user_quota_updates_on_commit(
    session: scoped_session[Session], send: Callable[[UserQuotaUpdates], None] | None
) -> None:
    """Pass the updates queued in ``session`` to ``send`` after each commit, or drop them if ``send`` is ``None``.

    The listeners apply to every session the scoped session's factory creates.
    """

    def after_commit(session: Session) -> None:
        updates = session.info.pop(_INFO_KEY, None)
        if send is None or updates is None:
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

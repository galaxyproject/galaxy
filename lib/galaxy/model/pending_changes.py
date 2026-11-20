"""Model changes collected per transaction, for publishers that send them once committed.

``session.info[PENDING_CHANGES]`` holds a ``PendingChanges`` only while a publisher listens on
the session (see ``galaxy.managers.change_events``), so recording is a no-op otherwise.
"""

from dataclasses import (
    dataclass,
    field,
)

from sqlalchemy.orm import Session

PENDING_CHANGES = "galaxy.pending_changes"


@dataclass
class PendingChanges:
    # {invocation_id: (owner_user_id, state)}
    invocations: dict[int, tuple[int | None, str]] = field(default_factory=dict)
    # {job_id: (user_id, galaxy_session_id, state)}
    jobs: dict[int, tuple[int | None, int | None, str]] = field(default_factory=dict)

    def copy(self) -> "PendingChanges":
        return PendingChanges(invocations=dict(self.invocations), jobs=dict(self.jobs))


def pending_changes(session: Session) -> PendingChanges | None:
    return session.info.get(PENDING_CHANGES)


def record_job_change(
    session: Session, job_id: int, user_id: int | None, galaxy_session_id: int | None, state: str
) -> None:
    pending = pending_changes(session)
    if pending is not None:
        pending.jobs[job_id] = (user_id, galaxy_session_id, str(state))

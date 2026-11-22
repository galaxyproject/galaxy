"""Model changes collected per transaction, for publishers that send them once committed.

``session.info[PENDING_CHANGES]`` holds a ``PendingChanges`` only while a publisher listens on
the session (see ``galaxy.managers.change_events``), so recording is a no-op otherwise.
"""

from dataclasses import (
    dataclass,
    field,
)
from typing import (
    TYPE_CHECKING,
    TypedDict,
)

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from galaxy.model import WorkflowInvocation

PENDING_CHANGES = "galaxy.pending_changes"


class InvocationUpdate(TypedDict):
    """A committed change to a workflow invocation's state, steps or messages.

    Routed to the owner of the invocation's history and to that history's viewers.
    """

    user_id: int | None
    history_id: int | None
    invocation_id: int
    state: str


class JobUpdate(TypedDict):
    """A committed job state change.

    Routed to the job's user or, for anonymous jobs, its session, and to the viewers of its history.
    """

    job_id: int
    state: str
    user_id: int | None
    session_id: int | None
    history_id: int | None


@dataclass
class PendingChanges:
    invocations: dict[int, InvocationUpdate] = field(default_factory=dict)
    jobs: dict[int, JobUpdate] = field(default_factory=dict)

    def copy(self) -> "PendingChanges":
        return PendingChanges(invocations=dict(self.invocations), jobs=dict(self.jobs))


def pending_changes(session: Session) -> PendingChanges | None:
    return session.info.get(PENDING_CHANGES)


def record_invocation_change(session: Session, invocation: "WorkflowInvocation", state: str) -> None:
    pending = pending_changes(session)
    if pending is None:
        return
    history = invocation.history
    pending.invocations[invocation.id] = InvocationUpdate(
        user_id=history.user_id if history else None,
        history_id=invocation.history_id,
        invocation_id=invocation.id,
        state=str(state),
    )


def record_job_change(
    session: Session,
    *,
    job_id: int,
    user_id: int | None,
    session_id: int | None,
    history_id: int | None,
    state: str,
) -> None:
    pending = pending_changes(session)
    if pending is not None:
        pending.jobs[job_id] = JobUpdate(
            job_id=job_id, state=str(state), user_id=user_id, session_id=session_id, history_id=history_id
        )

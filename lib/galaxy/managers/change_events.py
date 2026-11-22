"""Publish committed workflow invocation and job changes as SSE events.

Invocations and jobs change in many places and processes (queueing, scheduling iterations,
subworkflow invocations scheduled inside their parent's iteration, job handlers, runners,
cancellation, completion monitoring), and the commit is usually made by a caller far from the
change. Instead of an explicit dispatch after each commit, the publisher listens on the session
factory: changes are collected per transaction in a ``PendingChanges`` in ``session.info`` and
sent when the root transaction commits, so a client that refetches on receipt reads the change,
and rolled back changes are never sent.

An invocation counts as changed (``invocation_update``) when its state changes, when one of its
steps is added or changes state, or when a message is added to it. Steps advance while an
invocation stays ``ready``, and the invocation page shows them. A job counts as changed
(``job_update``) when its state changes; the event carries the job's state at commit. The
sources are:

- ORM changes, read from the unit of work in ``after_flush``: invocation state assignments
  (``cancel()``, ``fail()``, completion), new invocations, steps and messages, job state
  assignments (new jobs, ``mark_deleted()``, ``mark_stopped()``, ``mark_failed()``), and the
  ``JobStateHistory`` row that ``Job.set_state`` adds after its bulk ``UPDATE``.
- Bulk ``UPDATE`` statements, which bypass the unit of work and record themselves:
  ``WorkflowInvocation.set_state`` through ``record_invocation_change``, and the job
  cancellation in ``WorkflowInvocation.cancel_invocation_steps`` through ``record_job_change``.
"""

import logging
from collections import defaultdict
from itertools import chain

from sqlalchemy import (
    event,
    inspect,
)
from sqlalchemy.orm import (
    Session,
    SessionTransaction,
    UOWTransaction,
)
from sqlalchemy.orm.scoping import scoped_session

from galaxy.managers.sse_dispatch import SSEEventDispatcher
from galaxy.model import (
    Job,
    JobStateHistory,
    WorkflowInvocation,
    WorkflowInvocationMessage,
    WorkflowInvocationStep,
)
from galaxy.model.pending_changes import (
    JobUpdate,
    PENDING_CHANGES,
    pending_changes,
    PendingChanges,
    record_invocation_change,
    record_job_change,
)

log = logging.getLogger(__name__)

# ``session.info`` key holding, per open savepoint, a copy of the pending changes taken when the
# savepoint began. Releasing the savepoint drops its copy; a savepoint that ends with its copy
# still present was rolled back, and the copy is restored.
SAVEPOINT_SNAPSHOTS = "galaxy.pending_changes_savepoint_snapshots"

# A recipient with more job changes than this in one transaction gets a single resync event
# instead, which makes the client refetch the jobs it shows; so do the viewers of the histories
# those jobs belong to. Mapping a tool over a large collection creates that many jobs in one
# transaction.
MAX_JOBS_PER_EVENT = 500


class ChangeEventPublisher:
    def __init__(self, dispatcher: SSEEventDispatcher) -> None:
        self._dispatcher = dispatcher

    def register(self, session_factory: scoped_session[Session]) -> None:
        event.listen(session_factory, "after_transaction_create", self._after_transaction_create)
        event.listen(session_factory, "after_transaction_end", self._after_transaction_end)
        event.listen(session_factory, "after_flush", self._after_flush)
        event.listen(session_factory, "after_commit", self._after_commit)

    @staticmethod
    def _after_transaction_create(session: Session, transaction: SessionTransaction) -> None:
        if transaction.parent is None:
            # Each root transaction starts empty, which drops changes of rolled back transactions.
            session.info[PENDING_CHANGES] = PendingChanges()
            session.info[SAVEPOINT_SNAPSHOTS] = {}
        elif transaction.nested:
            pending = pending_changes(session)
            if pending is not None:
                session.info[SAVEPOINT_SNAPSHOTS][transaction] = pending.copy()

    @staticmethod
    def _after_transaction_end(session: Session, transaction: SessionTransaction) -> None:
        if transaction.nested:
            snapshot = session.info.get(SAVEPOINT_SNAPSHOTS, {}).pop(transaction, None)
            if snapshot is not None:
                session.info[PENDING_CHANGES] = snapshot

    @staticmethod
    def _after_flush(session: Session, flush_context: UOWTransaction) -> None:
        # ``session.new`` builds a new set on every access; a flush can hold thousands of objects.
        new = session.new
        for obj in chain(new, session.dirty):
            if isinstance(obj, WorkflowInvocation):
                added = inspect(obj).attrs.state.history.added
                if added and added[0] is not None:
                    record_invocation_change(session, obj, added[0])
            elif isinstance(obj, WorkflowInvocationStep):
                if obj in new or inspect(obj).attrs.state.history.added:
                    _record_current_state(session, obj.workflow_invocation)
            elif isinstance(obj, WorkflowInvocationMessage) and obj in new:
                _record_current_state(session, obj.workflow_invocation)
            elif isinstance(obj, Job):
                if inspect(obj).attrs.state.history.added:
                    _record_job(session, obj)
            elif isinstance(obj, JobStateHistory) and obj in new and obj.job_id:
                job = session.get(Job, obj.job_id)
                if job is not None:
                    _record_job(session, job)

    def _after_commit(self, session: Session) -> None:
        savepoint = session.get_nested_transaction()
        if savepoint is not None:
            # A released savepoint; its changes are sent when the root transaction commits.
            session.info.get(SAVEPOINT_SNAPSHOTS, {}).pop(savepoint, None)
            return
        pending = session.info.pop(PENDING_CHANGES, None)
        if pending is None:
            return
        if pending.invocations:
            self._send_invocation_updates(pending)
        if pending.jobs:
            self._send_job_updates(pending)

    def _send_invocation_updates(self, pending: PendingChanges) -> None:
        updates = [
            update
            for update in pending.invocations.values()
            if update["user_id"] is not None or update["history_id"] is not None
        ]
        if not updates:
            return
        try:
            self._dispatcher.invocation_update(updates)
        except Exception:
            # The commit is authoritative and the event is best effort; never fail the committer.
            log.exception(
                "Failed to dispatch invocation_update SSE event for invocations %s", list(pending.invocations)
            )

    def _send_job_updates(self, pending: PendingChanges) -> None:
        # Jobs grouped by (user_id, session_id) of the recipient; anonymous jobs route to their session.
        by_owner: dict[tuple[int | None, int | None], list[JobUpdate]] = defaultdict(list)
        for update in pending.jobs.values():
            user_id = update["user_id"]
            by_owner[(user_id, update["session_id"] if user_id is None else None)].append(update)
        updates: list[JobUpdate] = []
        resync_user_ids: list[int] = []
        resync_session_ids: list[int] = []
        resync_history_ids: set[int] = set()
        for (user_id, session_id), owner_updates in by_owner.items():
            if len(owner_updates) <= MAX_JOBS_PER_EVENT or (user_id is None and session_id is None):
                updates.extend(owner_updates)
                continue
            if user_id is not None:
                resync_user_ids.append(user_id)
            elif session_id is not None:
                resync_session_ids.append(session_id)
            resync_history_ids.update(u["history_id"] for u in owner_updates if u["history_id"] is not None)
        if not (updates or resync_user_ids or resync_session_ids):
            return
        try:
            self._dispatcher.job_update(
                updates,
                resync_user_ids=resync_user_ids,
                resync_session_ids=resync_session_ids,
                resync_history_ids=sorted(resync_history_ids),
            )
        except Exception:
            log.exception("Failed to dispatch job_update SSE event for %d jobs", len(pending.jobs))


def _record_job(session: Session, job: Job) -> None:
    if job.state is not None:
        record_job_change(
            session,
            job_id=job.id,
            user_id=job.user_id,
            session_id=job.session_id,
            history_id=job.history_id,
            state=job.state,
        )


def _record_current_state(session: Session, invocation: WorkflowInvocation) -> None:
    if invocation.state is not None:
        record_invocation_change(session, invocation, invocation.state)

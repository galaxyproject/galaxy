"""Publish workflow invocation changes as ``invocation_update`` SSE events once committed.

Invocations change in many places (queueing, materialization, every scheduling iteration,
subworkflow invocations scheduled inside their parent's iteration, cancellation, completion
monitoring) and are committed by the callers, often far from the change. Instead of an explicit
dispatch after each commit, the publisher listens on the session factory: changes are collected
per transaction in ``session.info`` and sent when the root transaction commits, so a client that
refetches on receipt reads the change, and rolled back changes are never sent.

An invocation counts as changed when its state changes, when one of its steps is added or
changes state, or when a message is added to it. Steps advance while an invocation stays
``ready``, and the invocation page shows them. The sources are:

- ORM changes (``invocation.state = ...``, ``cancel()``, ``fail()``, new invocations, steps and
  messages), read from the unit of work in ``after_flush``.
- ``WorkflowInvocation.set_state``'s conditional bulk ``UPDATE``, which records itself through
  ``record_invocation_change`` when a row actually changed.
"""

import logging
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
    PENDING_INVOCATION_CHANGES,
    record_invocation_change,
    WorkflowInvocation,
    WorkflowInvocationMessage,
    WorkflowInvocationStep,
)
from galaxy.queue_worker import InvocationUpdate

log = logging.getLogger(__name__)

# ``session.info`` key holding, per open savepoint, a copy of the pending changes taken when the
# savepoint began. Releasing the savepoint drops its copy; a savepoint that ends with its copy
# still present was rolled back, and the copy is restored.
SAVEPOINT_SNAPSHOTS = "galaxy.invocation_change_savepoint_snapshots"


class InvocationEventPublisher:
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
            session.info[PENDING_INVOCATION_CHANGES] = {}
            session.info[SAVEPOINT_SNAPSHOTS] = {}
        elif transaction.nested and PENDING_INVOCATION_CHANGES in session.info:
            session.info[SAVEPOINT_SNAPSHOTS][transaction] = dict(session.info[PENDING_INVOCATION_CHANGES])

    @staticmethod
    def _after_transaction_end(session: Session, transaction: SessionTransaction) -> None:
        if transaction.nested:
            snapshot = session.info.get(SAVEPOINT_SNAPSHOTS, {}).pop(transaction, None)
            if snapshot is not None:
                session.info[PENDING_INVOCATION_CHANGES] = snapshot

    @staticmethod
    def _after_flush(session: Session, flush_context: UOWTransaction) -> None:
        for obj in chain(session.new, session.dirty):
            if isinstance(obj, WorkflowInvocation):
                added = inspect(obj).attrs.state.history.added
                if added and added[0] is not None:
                    record_invocation_change(session, obj, added[0])
            elif isinstance(obj, WorkflowInvocationStep):
                if obj in session.new or inspect(obj).attrs.state.history.added:
                    _record_current_state(session, obj.workflow_invocation)
            elif isinstance(obj, WorkflowInvocationMessage) and obj in session.new:
                _record_current_state(session, obj.workflow_invocation)

    def _after_commit(self, session: Session) -> None:
        savepoint = session.get_nested_transaction()
        if savepoint is not None:
            # A released savepoint; its changes are sent when the root transaction commits.
            session.info.get(SAVEPOINT_SNAPSHOTS, {}).pop(savepoint, None)
            return
        pending = session.info.pop(PENDING_INVOCATION_CHANGES, None)
        if not pending:
            return
        # Invocations of anonymous users have no SSE route; their clients poll.
        updates = [
            InvocationUpdate(user_id=user_id, invocation_id=invocation_id, state=state)
            for invocation_id, (user_id, state) in pending.items()
            if user_id is not None
        ]
        if not updates:
            return
        try:
            self._dispatcher.invocation_update(updates)
        except Exception:
            # The commit is authoritative and the event is best effort; never fail the committer.
            log.exception("Failed to dispatch invocation_update SSE event for invocations %s", list(pending))


def _record_current_state(session: Session, invocation: WorkflowInvocation) -> None:
    if invocation.state is not None:
        record_invocation_change(session, invocation, invocation.state)

"""
Manager for workflow invocation completion detection and recording.

This module provides the WorkflowCompletionManager class which handles:
- Checking if workflow invocations have completed
- Recording completion details in the database
- Polling for invocations that need completion checks
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm.scoping import scoped_session

from galaxy.model import (
    WorkflowInvocation,
    WorkflowInvocationCompletion,
)
from galaxy.schema.invocation import InvocationState
from galaxy.structured_app import MinimalManagerApp
from galaxy.workflow.completion import compute_job_state_summary

log = logging.getLogger(__name__)


class WorkflowCompletionManager:
    """
    Manages workflow completion detection and recording.

    This manager checks workflow invocations for completion (all jobs in terminal
    states) and records completion details including job state summaries.
    """

    def __init__(self, app: MinimalManagerApp):
        self.app = app

    @property
    def sa_session(self) -> scoped_session:
        return self.app.model.context

    def check_and_record_completion(self, invocation_id: int) -> Optional[WorkflowInvocationCompletion]:
        """
        Check if invocation is complete and record completion if so.

        This method is idempotent - if the invocation already has a completion
        record, it will not create a duplicate.

        Args:
            invocation_id: The ID of the workflow invocation to check.

        Returns:
            The WorkflowInvocationCompletion record if newly completed,
            None if already completed or not yet complete.
        """
        log.debug("Checking completion for invocation %d", invocation_id)
        session = self.sa_session

        # Use select to get fresh data from database
        stmt = select(WorkflowInvocation).where(WorkflowInvocation.id == invocation_id)
        invocation = session.execute(stmt).scalar_one_or_none()
        if not invocation:
            log.debug("Invocation %d not found", invocation_id)
            return None

        log.debug(
            "Invocation %d state=%s, has_completion=%s",
            invocation_id,
            invocation.state,
            invocation.completion is not None,
        )

        # Already completed - don't create duplicate record
        if invocation.completion is not None:
            log.debug("Invocation %d already has completion record", invocation_id)
            return None

        # Check if complete
        complete = invocation.is_complete
        log.debug("Invocation %d is_complete=%s", invocation_id, complete)
        if not complete:
            return None

        # Record completion
        job_summary = compute_job_state_summary(invocation)
        log.debug("Invocation %d job_summary=%s", invocation_id, job_summary)

        completion = WorkflowInvocationCompletion(
            workflow_invocation_id=invocation.id,
            job_state_summary=job_summary,
            hooks_executed=[],
        )

        # Update invocation state to COMPLETED
        invocation.state = InvocationState.COMPLETED.value

        session.add(completion)
        session.commit()
        log.info("Recorded completion for invocation %d", invocation_id)

        return completion

    def poll_pending_completions(self, limit: int = 100, handler: Optional[str] = None) -> list[int]:
        """
        Find invocations that are SCHEDULED but not yet recorded as complete.

        These are invocations that have had all their steps scheduled but
        haven't been checked for job completion yet.

        Args:
            limit: Maximum number of invocation IDs to return.
            handler: If provided, only return invocations assigned to this handler.

        Returns:
            List of invocation IDs to check for completion.
        """
        stmt = (
            select(WorkflowInvocation.id)
            .outerjoin(
                WorkflowInvocationCompletion,
                WorkflowInvocation.id == WorkflowInvocationCompletion.workflow_invocation_id,
            )
            .where(WorkflowInvocation.state == InvocationState.SCHEDULED.value)
            .where(WorkflowInvocationCompletion.id.is_(None))
        )
        if handler is not None:
            stmt = stmt.where(WorkflowInvocation.handler == handler)
        stmt = stmt.limit(limit)
        session = self.sa_session
        result = list(session.execute(stmt).scalars())
        if result:
            log.debug("Found %d pending completions: %s", len(result), result)
        return result

    def get_completion(self, invocation_id: int) -> Optional[WorkflowInvocationCompletion]:
        """
        Get the completion record for an invocation.

        Args:
            invocation_id: The ID of the workflow invocation.

        Returns:
            The WorkflowInvocationCompletion record if it exists, None otherwise.
        """
        stmt = select(WorkflowInvocationCompletion).where(
            WorkflowInvocationCompletion.workflow_invocation_id == invocation_id
        )
        session = self.sa_session
        return session.execute(stmt).scalar_one_or_none()

    def mark_hook_executed(self, invocation_id: int, hook_name: str) -> bool:
        """
        Mark a hook as executed for an invocation.

        This is used to ensure idempotency - hooks won't be executed twice
        for the same invocation.

        Args:
            invocation_id: The ID of the workflow invocation.
            hook_name: The name of the hook that was executed.

        Returns:
            True if the hook was marked as executed (or already was),
            False if the completion record doesn't exist.
        """
        session = self.sa_session
        stmt = select(WorkflowInvocationCompletion).where(
            WorkflowInvocationCompletion.workflow_invocation_id == invocation_id
        )
        completion = session.execute(stmt).scalar_one_or_none()
        if not completion:
            return False

        hooks_executed = completion.hooks_executed or []
        if hook_name not in hooks_executed:
            hooks_executed.append(hook_name)
            completion.hooks_executed = hooks_executed
            session.commit()

        return True

    def is_hook_executed(self, invocation_id: int, hook_name: str) -> bool:
        """
        Check if a hook has already been executed for an invocation.

        Args:
            invocation_id: The ID of the workflow invocation.
            hook_name: The name of the hook to check.

        Returns:
            True if the hook has been executed, False otherwise.
        """
        completion = self.get_completion(invocation_id)
        if not completion:
            return False

        hooks_executed = completion.hooks_executed or []
        return hook_name in hooks_executed

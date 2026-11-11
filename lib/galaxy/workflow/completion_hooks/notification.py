"""
Notification workflow completion hook.

This hook sends a notification to the user when their workflow completes.
"""

import logging

__all__ = ("SendNotificationHook",)

from typing import TYPE_CHECKING

from galaxy.schema.notifications import (
    completion_notification_request,
    WorkflowCompletionNotificationContent,
)
from galaxy.workflow.completion_hooks.base import WorkflowCompletionHook

if TYPE_CHECKING:
    from galaxy.model import WorkflowInvocationCompletion

log = logging.getLogger(__name__)


class SendNotificationHook(WorkflowCompletionHook):
    """
    Hook that sends a notification when a workflow completes.

    Uses Galaxy's notification system to notify the user that their
    workflow has completed. The notification includes the workflow name
    and a summary of job states.
    """

    plugin_type = "send_notification"

    def execute(self, completion: "WorkflowInvocationCompletion") -> None:
        """
        Send a notification for the completed workflow.

        Args:
            completion: The completion record.
        """
        invocation = completion.workflow_invocation
        history = invocation.history
        user = history.user if history else None

        if not user:
            log.debug(
                "No user associated with invocation %d, skipping notification",
                invocation.id,
            )
            return

        state_counts = completion.job_state_summary or {}
        content = WorkflowCompletionNotificationContent(
            history_id=self.app.security.encode_id(history.id),
            history_name=history.name or "Unnamed history",
            workflow_name=self._get_workflow_name(invocation),
            job_count=sum(state_counts.values()),
            state_counts=state_counts,
            invocation_id=self.app.security.encode_id(invocation.id),
        )
        request = completion_notification_request(user.id, content, self.app.config.galaxy_infrastructure_url)

        # Send the notification
        try:
            notification_manager = self.app.notification_manager
            notification, count = notification_manager.send_notification_to_recipients(request)
            if notification:
                log.info(
                    "Sent workflow completion notification to user %d for invocation %d",
                    user.id,
                    invocation.id,
                )
            else:
                log.debug(
                    "User %d opted out of workflow completion notifications",
                    user.id,
                )
        except Exception:
            log.exception(
                "Failed to send notification to user %d for invocation %d",
                user.id,
                invocation.id,
            )
            raise

    def _get_workflow_name(self, invocation) -> str:
        """
        Get the name of the workflow.

        Args:
            invocation: The workflow invocation.

        Returns:
            The workflow name, or "Unknown Workflow" if not available.
        """
        try:
            return invocation.workflow.stored_workflow.name
        except AttributeError:
            return "Unknown Workflow"

    def is_applicable(self, completion: "WorkflowInvocationCompletion") -> bool:
        """
        Check if this hook should run.

        Only applicable if the user requested notifications when submitting
        the workflow (by including 'send_notification' in the on_complete list).

        Args:
            completion: The completion record.

        Returns:
            True if notification was requested and a user is associated.
        """
        invocation = completion.workflow_invocation
        history = invocation.history
        if history is None or history.user is None:
            return False

        # Check if send_notification was requested in on_complete
        on_complete = invocation.on_complete or []
        for action in on_complete:
            if isinstance(action, dict) and "send_notification" in action:
                return True
        return False

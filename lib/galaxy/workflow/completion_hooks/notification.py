"""
Notification workflow completion hook.

This hook sends a notification to the user when their workflow completes.
"""

import logging
from typing import TYPE_CHECKING

from galaxy.schema.notifications import (
    MessageNotificationContent,
    NotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
    NotificationVariant,
    PersonalNotificationCategory,
)
from galaxy.workflow.completion_hooks.base import WorkflowCompletionHook

if TYPE_CHECKING:
    from galaxy.model import WorkflowInvocationCompletion

log = logging.getLogger(__name__)


class SendNotificationHook(WorkflowCompletionHook):
    """
    Hook that sends a notification when a workflow completes.

    Uses Galaxy's notification system to notify the user that their
    workflow has completed. The notification includes the workflow name,
    completion status, and a summary of job states.
    """

    name = "send_notification"

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

        # Get workflow name
        workflow_name = self._get_workflow_name(invocation)

        # Build notification content
        status = "successfully" if completion.all_jobs_ok else "with errors"
        subject = f"Workflow '{workflow_name}' completed {status}"
        message = self._build_message(completion, workflow_name)

        # Determine notification variant based on success
        variant = NotificationVariant.info if completion.all_jobs_ok else NotificationVariant.warning

        # Create the notification request
        notification_data = NotificationCreateData(
            source="galaxy",
            category=PersonalNotificationCategory.message,
            variant=variant,
            content=MessageNotificationContent(
                subject=subject,
                message=message,
            ),
        )

        recipients = NotificationRecipients(user_ids=[user.id])

        request = NotificationCreateRequest(
            recipients=recipients,
            notification=notification_data,
            galaxy_url=self.app.config.galaxy_infrastructure_url,
        )

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

    def _build_message(self, completion: "WorkflowInvocationCompletion", workflow_name: str) -> str:
        """
        Build the notification message.

        Args:
            completion: The completion record.
            workflow_name: The name of the workflow.

        Returns:
            The formatted message string with Markdown.
        """
        invocation = completion.workflow_invocation
        summary = completion.job_state_summary or {}

        lines = [
            f"Your workflow **{workflow_name}** has completed.",
            "",
        ]

        if completion.all_jobs_ok:
            lines.append("All jobs completed successfully.")
        else:
            lines.append("Some jobs encountered errors.")

        if summary:
            lines.extend(["", "**Job Summary:**", ""])
            for state, count in sorted(summary.items()):
                lines.append(f"- {state}: {count}")

        # Add link to invocation if possible
        try:
            encoded_id = self.app.security.encode_id(invocation.id)
            infrastructure_url = self.app.config.galaxy_infrastructure_url
            if infrastructure_url:
                invocation_url = f"{infrastructure_url}/workflows/invocations/{encoded_id}"
                lines.extend(["", f"[View Invocation Details]({invocation_url})"])
        except Exception:
            # Don't fail if we can't generate the link
            pass

        return "\n".join(lines)

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

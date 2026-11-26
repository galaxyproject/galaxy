"""Register notification watches for invocations submitted before monitor-based delivery."""

from typing import TYPE_CHECKING

from galaxy.workflow.completion_hooks.base import WorkflowCompletionHook

if TYPE_CHECKING:
    from galaxy.model import WorkflowInvocationCompletion

__all__ = ("SendNotificationHook",)


class SendNotificationHook(WorkflowCompletionHook):
    plugin_type = "send_notification"

    def execute(self, completion: "WorkflowInvocationCompletion", *, commit: bool = True) -> None:
        completion.workflow_invocation.request_notifications()
        if commit:
            self.app.model.context.commit()

    def is_applicable(self, completion: "WorkflowInvocationCompletion") -> bool:
        invocation = completion.workflow_invocation
        return bool(
            invocation.history
            and invocation.history.user
            and any(
                isinstance(action, dict) and "send_notification" in action for action in invocation.on_complete or []
            )
        )

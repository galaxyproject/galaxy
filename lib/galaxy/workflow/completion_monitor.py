"""
Background monitor for workflow invocation completion.

This module provides the WorkflowCompletionMonitor class which runs in a
background thread and monitors workflow invocations for completion,
recording completion details and triggering hooks when workflows finish.
"""

import logging
from typing import (
    TYPE_CHECKING,
)

from galaxy.celery.tasks import execute_workflow_completion_hook
from galaxy.util.monitors import Monitors

if TYPE_CHECKING:
    from galaxy.managers.workflow_completion import WorkflowCompletionManager
    from galaxy.structured_app import MinimalManagerApp
    from galaxy.workflow.completion_hooks import WorkflowCompletionHookRegistry

log = logging.getLogger(__name__)


class WorkflowCompletionMonitor(Monitors):
    """
    Background monitor that checks for completed workflow invocations
    and triggers completion hooks.

    This monitor runs in a daemon thread and periodically:
    1. Polls for SCHEDULED invocations without completion records
    2. Checks if all jobs have reached terminal states
    3. Records completion details in the database
    4. Queues Celery tasks to execute registered hooks
    """

    def __init__(
        self,
        app: "MinimalManagerApp",
        completion_manager: "WorkflowCompletionManager",
        hook_registry: "WorkflowCompletionHookRegistry",
    ) -> None:
        """
        Initialize the completion monitor.

        Args:
            app: The Galaxy application instance.
            completion_manager: Manager for completion detection and recording.
            hook_registry: Registry of completion hooks to execute.
        """
        self.app = app
        self.completion_manager = completion_manager
        self.hook_registry = hook_registry
        self.monitor_sleep_time = app.config.workflow_completion_monitor_sleep
        self._init_monitor_thread(
            name="WorkflowCompletionMonitor.monitor_thread",
            target=self._monitor,
            config=app.config,
        )

    def start(self) -> None:
        """Start the monitor thread."""
        log.info("Starting workflow completion monitor")
        self.monitor_thread.start()

    def _monitor(self) -> None:
        """Main monitoring loop."""
        while self.monitor_running:
            try:
                self._monitor_step()
            except Exception:
                log.exception("Error in workflow completion monitor step")
            self._monitor_sleep(self.monitor_sleep_time)

    def _monitor_step(self) -> None:
        """
        Single iteration of the monitoring loop.

        Polls for pending completions and processes each one.
        Only monitors invocations assigned to this handler.
        """
        try:
            # Find SCHEDULED invocations without completion records
            # Only poll invocations assigned to this handler
            handler = self.app.config.server_name
            pending_ids = self.completion_manager.poll_pending_completions(handler=handler)

            if pending_ids:
                log.debug(
                    "Workflow completion monitor checking %d invocations",
                    len(pending_ids),
                )

            for invocation_id in pending_ids:
                if not self.monitor_running:
                    return

                try:
                    self._check_invocation(invocation_id)
                except Exception:
                    log.exception("Error checking completion for invocation %d", invocation_id)
        finally:
            # Release database connection back to the pool
            self.app.model.context.remove()

    def _check_invocation(self, invocation_id: int) -> None:
        """
        Check a single invocation for completion.

        If the invocation is complete, records completion and queues hooks.

        Args:
            invocation_id: The ID of the invocation to check.
        """
        completion = self.completion_manager.check_and_record_completion(invocation_id)

        if completion:
            log.info(
                "Workflow invocation %d completed (all_jobs_ok=%s)",
                invocation_id,
                completion.all_jobs_ok,
            )
            self._queue_completion_hooks(completion)

    def _queue_completion_hooks(self, completion) -> None:
        """
        Queue Celery tasks for hooks requested by the user.

        Args:
            completion: The completion record for the invocation.
        """
        invocation = completion.workflow_invocation
        on_complete = invocation.on_complete or []

        if not on_complete:
            log.debug(
                "No on_complete actions requested for invocation %d",
                invocation.id,
            )
            return

        # Extract action names from action objects
        # Each action is a dict like {"export_to_file_source": {...config...}}
        available_hooks = self.hook_registry.get_available_hooks()
        hooks_to_queue = []
        for action in on_complete:
            if isinstance(action, dict):
                for action_name in action.keys():
                    if action_name in available_hooks:
                        hooks_to_queue.append(action_name)
                    else:
                        log.warning(
                            "Unknown on_complete action '%s' for invocation %d",
                            action_name,
                            invocation.id,
                        )

        if not hooks_to_queue:
            log.debug(
                "No matching hooks for on_complete actions in invocation %d",
                invocation.id,
            )
            return

        log.debug(
            "Queuing %d completion hooks for invocation %d: %s",
            len(hooks_to_queue),
            invocation.id,
            hooks_to_queue,
        )

        for hook_name in hooks_to_queue:
            try:
                execute_workflow_completion_hook.delay(
                    invocation_id=invocation.id,
                    hook_name=hook_name,
                )
            except Exception:
                log.exception(
                    "Error queuing hook '%s' for invocation %d",
                    hook_name,
                    invocation.id,
                )

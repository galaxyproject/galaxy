"""Check completion-hook dispatch through the monitor's deferred task import."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from galaxy.workflow.completion_monitor import WorkflowCompletionMonitor


def test_queue_requested_completion_hooks(mocker):
    queue_hook = mocker.patch("galaxy.celery.tasks.execute_workflow_completion_hook.delay")
    hook_registry = MagicMock()
    hook_registry.get_available_hooks.return_value = {"export_to_file_source": MagicMock()}
    app = MagicMock()
    app.config.workflow_completion_monitor_sleep = 1
    app.config.monitor_thread_join_timeout = 0
    monitor = WorkflowCompletionMonitor(app, MagicMock(), hook_registry)
    invocation = SimpleNamespace(id=42, on_complete=[{"export_to_file_source": {}}, {"unknown_hook": {}}])
    try:
        monitor._queue_completion_hooks(SimpleNamespace(workflow_invocation=invocation))
        queue_hook.assert_called_once_with(invocation_id=42, hook_name="export_to_file_source")
    finally:
        monitor.shutdown_monitor()

from galaxy.web_stack.message import (
    JobHandlerMessage,
    WorkflowSchedulingMessage,
)


def test_validate_job_handler_message():
    message = JobHandlerMessage(task="setup", job_id=42)
    message.validate()

    message = JobHandlerMessage(task="setup")
    error = None
    try:
        message.validate()
    except AssertionError as e:
        error = e
    assert error is not None


def test_validate_workflow_handler_message():
    message = WorkflowSchedulingMessage(task="setup", workflow_invocation_id=42)
    message.validate()

    message = WorkflowSchedulingMessage(task="setup")
    error = None
    try:
        message.validate()
    except AssertionError as e:
        error = e
    assert error is not None

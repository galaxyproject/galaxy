"""The output changes a rerun form restores from the post job actions of a job."""

from galaxy import model
from galaxy.schema.tool_outputs import ToolOutputActions
from galaxy.tools.output_actions import output_actions_of_job


def _job_with(*post_job_actions: model.PostJobAction) -> model.Job:
    job = model.Job()
    for pja in post_job_actions:
        job.add_post_job_action(pja)
    return job


def test_leaves_out_actions_that_are_not_output_changes():
    job = _job_with(
        model.PostJobAction("HideDatasetAction", output_name="out_file1"),
        model.PostJobAction("ChangeDatatypeAction", output_name="out_file2", action_arguments={"newtype": "txt"}),
    )

    assert output_actions_of_job(job) == {"out_file1": ToolOutputActions(hide=True)}


def test_has_no_changes_for_a_job_of_a_workflow_invocation():
    # Runtime actions of a workflow run have no workflow step but still belong to the workflow.
    job = _job_with(model.PostJobAction("HideDatasetAction", output_name="out_file1"))
    invocation_step = model.WorkflowInvocationStep()
    invocation_step.job = job

    assert output_actions_of_job(job) == {}


def test_leaves_out_actions_copied_from_a_workflow_step():
    # A rerun of a workflow job copies the step's actions onto a job that has no invocation step.
    step = model.WorkflowStep()
    job = _job_with(
        model.PostJobAction("RenameDatasetAction", step, output_name="out_file1", action_arguments={"newname": "x"})
    )

    assert output_actions_of_job(job) == {}

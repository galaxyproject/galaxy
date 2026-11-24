"""The output changes a rerun form restores from the post job actions of a job."""

from galaxy import model
from galaxy.tools.output_actions import output_actions_of_job


def _job_with(*post_job_actions: model.PostJobAction) -> model.Job:
    job = model.Job()
    for pja in post_job_actions:
        job.add_post_job_action(pja)
    return job


def test_has_no_changes_for_a_job_of_a_workflow_invocation():
    # Runtime actions of a workflow run have no workflow step but still belong to the workflow.
    job = _job_with(model.PostJobAction("HideDatasetAction", output_name="out_file1"))
    invocation_step = model.WorkflowInvocationStep()
    invocation_step.job = job

    assert output_actions_of_job(job) == {}

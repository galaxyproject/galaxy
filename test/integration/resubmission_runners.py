import time

from galaxy import model
from galaxy.jobs.runners import (
    JobState
)
from galaxy.jobs.runners.local import LocalJobRunner


class FailsJobRunner(LocalJobRunner):
    """Job runner that fails with runner state specified via job resource parameters."""

    def queue_job(self, job_wrapper):
        if not self._prepare_job_local(job_wrapper):
            return

        resource_parameters = job_wrapper.get_resource_parameters()
        failure_state = resource_parameters.get("failure_state", None)

        if failure_state in (JobState.runner_states.WALLTIME_REACHED, JobState.runner_states.MEMORY_LIMIT_REACHED):
            job_wrapper.change_state(model.Job.states.RUNNING)
            run_for = int(resource_parameters.get("run_for", 0))
            if run_for > 0:
                time.sleep(run_for)

        job_state = JobState(
            job_wrapper,
            job_wrapper.job_destination
        )
        if failure_state is not None:
            job_state.runner_state = failure_state
        job_state.stop_job = False
        self.fail_job(job_state, exception=True)


class AssertionJobRunner(LocalJobRunner):
    """Job runner that knows about test cases and checks final state assumptions."""

    def queue_job(self, job_wrapper):
        resource_parameters = job_wrapper.get_resource_parameters()
        try:
            test_name = resource_parameters["test_name"]
        except KeyError:
            job_wrapper.fail("Job resource parameter test_name not set as required for this job runner.")
            return

        job_dest_params = job_wrapper.job_destination.params

        if test_name == "test_walltime_resubmission":
            assert job_dest_params["dest_name"] == "retry_test_more_walltime"
        elif test_name == "test_memory_resubmission":
            assert job_dest_params["dest_name"] == "retry_test_more_mem"
        elif test_name == "test_unknown_error":
            assert job_dest_params["dest_name"] == "retry_unknown_error"

        super(AssertionJobRunner, self).queue_job(job_wrapper)


__all__ = ('FailsJobRunner', 'AssertionJobRunner')

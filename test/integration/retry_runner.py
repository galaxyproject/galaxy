from galaxy.jobs.runners import (
    JobState
)
from galaxy.jobs.runners.local import LocalJobRunner


class RetryJobRunner(LocalJobRunner):
    # TODO: It may be possible to do this with destinations instead of a runner.

    def __init__(self, *args, **kwds):
        super(RetryJobRunner, self).__init__(*args, **kwds)
        self.job_counts = {}

    def queue_job(self, job_wrapper):
        resource_parameters = job_wrapper.get_resource_parameters()
        job_dest_params = job_wrapper.job_destination.params
        try:
            test_name = resource_parameters["test_name"]
        except KeyError:
            job_wrapper.fail("Job resource parameters not set as required for this job runner.")
            return

        job_count = self.job_counts.get(test_name, 0)
        if str(job_count + 1) != job_dest_params.get("try_count", "-1"):
            job_wrapper.fail("Non-tool failure!")
            return

        def fail_with_runner_state(runner_state):
            job_state = JobState(
                job_wrapper,
                job_wrapper.job_destination
            )
            job_state.runner_state = runner_state
            self.fail_job(job_state, exception=True)

        try:
            failed = False
            if job_count == 0:
                if test_name == "test_job_resources":
                    pass
                elif test_name == "test_walltime_resubmission":
                    fail_with_runner_state(JobState.runner_states.WALLTIME_REACHED)
                    self.fail_job(JobState, exception=True)
                    failed = True
                elif test_name == "test_memory_resubmission":
                    fail_with_runner_state(JobState.runner_states.MEMORY_LIMIT_REACHED)
                    failed = True
                else:
                    job_wrapper.fail("Non-tool failure!")
                    failed = True
            if job_count == 1:
                if test_name == "test_walltime_resubmission":
                    assert job_dest_params["dest_name"] == "retry_test_more_walltime"
                elif test_name == "test_memory_resubmission":
                    assert job_dest_params["dest_name"] == "retry_test_more_mem"
            if not failed:
                super(RetryJobRunner, self).queue_job(job_wrapper)

        finally:
            self.job_counts[test_name] = job_count + 1


__all__ = ('RetryJobRunner')

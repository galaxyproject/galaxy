from galaxy.jobs.job_destination import JobDestination

DEFAULT_INITIAL_ENVIRONMENT = "fail_first_try"


def initial_target_environment(resource_params):
    return resource_params.get("initial_target_environment", None) or DEFAULT_INITIAL_ENVIRONMENT


def dynamic_resubmit_once(resource_params) -> JobDestination:
    """Build environment that always fails first time and always re-routes to passing environment."""
    return JobDestination(
        # Always fail on the first attempt.
        runner="failure_runner",
        # Resubmit to a valid environment.
        resubmit=[
            dict(
                condition="any_failure",
                environment="local",
            )
        ],
    )

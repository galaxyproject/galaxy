from galaxy.jobs import JobDestination

DEFAULT_INITIAL_ENVIRONMENT = "fail_first_try"


def initial_target_environment(resource_params):
    return resource_params.get("initial_target_environment", None) or DEFAULT_INITIAL_ENVIRONMENT


def dynamic_resubmit_once(resource_params):
    """Build environment that always fails first time and always re-routes to passing environment."""
    job_destination = JobDestination()
    # Always fail on the first attempt.
    job_destination["runner"] = "failure_runner"
    # Resubmit to a valid environment.
    job_destination["resubmit"] = [
        dict(
            condition="any_failure",
            environment="local",
        )
    ]
    return job_destination


def dynamic_resubmit_initial(resource_params):
    job_destination = JobDestination()
    job_destination["id"] = "initial_destination"
    # Always fail on the first attempt.
    job_destination["runner"] = "failure_runner"
    # Resubmit to a valid environment.
    job_destination["resubmit"] = [
        dict(
            condition="any_failure",
            destination="secondary_destination",
        )
    ]
    return job_destination


def dynamic_resubmit_secondary(resource_params):
    job_destination = JobDestination()
    job_destination["id"] = "secondary_destination"
    # Always fail on the first attempt.
    job_destination["runner"] = "failure_runner"
    # Resubmit to a valid environment.
    job_destination["resubmit"] = [
        dict(
            condition="any_failure",
            destination="tertiary_destination",
        )
    ]
    return job_destination


def dynamic_resubmit_tertiary(resource_params):
    job_destination = JobDestination()
    # Always fail on the first attempt.
    job_destination["id"] = "tertiary_destination"
    job_destination["runner"] = "failure_runner"
    # Resubmit to a valid environment.
    job_destination["resubmit"] = [
        dict(
            condition="any_failure",
            environment="local",
        )
    ]
    return job_destination

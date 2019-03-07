from galaxy.jobs import JobDestination

DEFAULT_INITIAL_DESTINATION = "fail_first_try"


def initial_destination(resource_params):
    return resource_params.get("initial_destination", None) or DEFAULT_INITIAL_DESTINATION


def dynamic_resubmit_once(resource_params):
    """Build destination that always fails first time and always re-routes to passing destination."""
    job_destination = JobDestination()
    # Always fail on the first attempt.
    job_destination['runner'] = "failure_runner"
    # Resubmit to a valid destination.
    job_destination['resubmit'] = [dict(
        condition="any_failure",
        destination="local",
    )]
    return job_destination

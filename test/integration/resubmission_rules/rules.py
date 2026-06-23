from galaxy.jobs.job_destination import JobDestination
from galaxy.jobs.mapper import JobMappingException

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


def _expected_chain_attempt(job, expected: int) -> None:
    """Assert the prior attempt's destination_params carried forward.

    Reaching the secondary/tertiary rules with the right `chain_attempt` in
    `job.destination_params` requires both (a) multiple resubmits to walk the
    chain afresh on each pickup, and (b) the resubmit handler to merge the
    prior attempt's destination_params into the persisted dispatcher so the
    rule sees them on re-entry. Raising here surfaces a regression as a
    JobMappingException rather than silently producing a wrong result.
    """
    actual = int((job.destination_params or {}).get("chain_attempt", 0))
    if actual != expected:
        raise JobMappingException(f"chain_attempt carry-forward broken: expected {expected}, got {actual}")


def dynamic_resubmit_initial(job) -> JobDestination:
    """First link of a chained dynamic destination: fail and resubmit to the second link."""
    _expected_chain_attempt(job, 0)
    return JobDestination(
        runner="failure_runner",
        params={"chain_attempt": 1},
        resubmit=[
            dict(
                condition="any_failure",
                environment="secondary_destination",
            )
        ],
    )


def dynamic_resubmit_secondary(job) -> JobDestination:
    """Second link: fail and resubmit to the third link.

    Reaching this rule on the *second* resubmit-attempt requires that the
    chain re-evaluates from the persisted dynamic intent rather than from
    the cached resolved destination of the previous attempt. Asserting on
    `chain_attempt == 1` additionally requires that destination_params from
    the prior attempt survived the resubmit handler.
    """
    _expected_chain_attempt(job, 1)
    return JobDestination(
        runner="failure_runner",
        params={"chain_attempt": 2},
        resubmit=[
            dict(
                condition="any_failure",
                environment="tertiary_destination",
            )
        ],
    )


def dynamic_resubmit_tertiary(job) -> JobDestination:
    """Third link: succeed on the local runner.

    Asserts the counter reached 2 to confirm both resubmits carried params.
    """
    _expected_chain_attempt(job, 2)
    return JobDestination(runner="local")

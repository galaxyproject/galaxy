"""What Galaxy does with each reason a job runner, or a Pulsar server, reports for a failed job.

The reasons themselves are the ``runner_states`` shared with Pulsar. What users are told
and whether a job is resubmitted are Galaxy's decisions, so they are kept here.
"""

from typing import NamedTuple

from galaxy.jobs.runners.util import runner_states


class RunnerStateDefinition(NamedTuple):
    value: str
    # Shown to the user when the runner has nothing more specific to say.
    fail_message: str | None = None
    # Completes "Job will be resubmitted because ...", None means jobs are never resubmitted for this state.
    resubmit_description: str | None = None
    # Name of the boolean variable offered to resubmit conditions, if any.
    condition: str | None = None


RUNNER_STATE_DEFINITIONS: dict[str, RunnerStateDefinition] = {}


def register_runner_state(
    name: str,
    value: str,
    fail_message: str | None = None,
    resubmit_description: str | None = None,
    condition: str | None = None,
) -> str:
    """Declare a reason a job can fail, this is all a runner needs to do to report a new one.

    ``name`` becomes an attribute of ``runner_states``. Returns ``value``.
    """
    definition = RunnerStateDefinition(value, fail_message, resubmit_description, condition)
    if runner_states.get(name, value) != value or RUNNER_STATE_DEFINITIONS.setdefault(value, definition) != definition:
        raise ValueError(f"Runner state {name} [{value}] is already registered with a different definition")
    setattr(runner_states, name, value)
    return value


register_runner_state(
    "WALLTIME_REACHED",
    runner_states.WALLTIME_REACHED,
    fail_message="This job was terminated because it ran longer than the maximum allowed job run time.",
    resubmit_description="it reached the walltime",
    condition="walltime_reached",
)
register_runner_state(
    "MEMORY_LIMIT_REACHED",
    runner_states.MEMORY_LIMIT_REACHED,
    fail_message="This job was terminated because it used more memory than it was allocated.",
    resubmit_description="it exceeded the amount of allocated memory",
    condition="memory_limit_reached",
)
register_runner_state(
    "JOB_OUTPUT_NOT_RETURNED_FROM_CLUSTER",
    runner_states.JOB_OUTPUT_NOT_RETURNED_FROM_CLUSTER,
    resubmit_description="its output was not returned from the cluster",
    condition="job_output_not_returned_from_cluster",
)
register_runner_state(
    "UNKNOWN_ERROR",
    runner_states.UNKNOWN_ERROR,
    fail_message="This job ran into an unknown error.",
    resubmit_description="it encountered an unknown error",
    condition="unknown_error",
)
register_runner_state("GLOBAL_WALLTIME_REACHED", runner_states.GLOBAL_WALLTIME_REACHED)
register_runner_state(
    "TOOL_TIMELIMIT_REACHED",
    runner_states.TOOL_TIMELIMIT_REACHED,
    resubmit_description="it exceeded the tool's time limit",
    condition="tool_timelimit_reached",
)
register_runner_state("OUTPUT_SIZE_LIMIT", runner_states.OUTPUT_SIZE_LIMIT)
register_runner_state(
    "TOOL_DETECT_ERROR",
    runner_states.TOOL_DETECT_ERROR,
    resubmit_description="it encountered a tool detected error condition",
    condition="tool_detected_failure",
)
register_runner_state(
    "NODE_FAILURE",
    runner_states.NODE_FAILURE,
    fail_message="This job failed because a node it was running on failed.",
    resubmit_description="a node it was running on failed",
    condition="node_failure",
)
register_runner_state(
    "PREEMPTED",
    runner_states.PREEMPTED,
    fail_message="This job was stopped because it was preempted by a higher priority job.",
    resubmit_description="it was preempted",
    condition="preempted",
)
# Stopped on purpose by someone outside of Galaxy, so never resubmitted.
register_runner_state(
    "CANCELLED",
    runner_states.CANCELLED,
    fail_message="This job failed because it was cancelled by an administrator.",
)


__all__ = (
    "RUNNER_STATE_DEFINITIONS",
    "RunnerStateDefinition",
    "register_runner_state",
)

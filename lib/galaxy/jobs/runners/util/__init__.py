"""
This module and its submodules contains utilities for running external
processes and interfacing with job managers. This module should contain
functionality shared between Galaxy and the Pulsar.
"""

from __future__ import annotations

from typing import NamedTuple

from galaxy.util.bunch import Bunch
from .kill import kill_pid


class RunnerStateDefinition(NamedTuple):
    """What Galaxy needs to know about one reason a job can fail."""

    value: str
    # Shown to the user when the runner has nothing more specific to say.
    fail_message: str | None = None
    # Completes "Job will be resubmitted because ...", None means jobs are never resubmitted for this state.
    resubmit_description: str | None = None
    # Name of the boolean variable offered to resubmit conditions, if any.
    condition: str | None = None


runner_states = Bunch()
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
    if RUNNER_STATE_DEFINITIONS.setdefault(value, definition) != definition:
        raise ValueError(f"Runner state [{value}] is already registered with a different definition")
    setattr(runner_states, name, value)
    return value


register_runner_state(
    "WALLTIME_REACHED",
    "walltime_reached",
    fail_message="This job was terminated because it ran longer than the maximum allowed job run time.",
    resubmit_description="it reached the walltime",
    condition="walltime_reached",
)
register_runner_state(
    "MEMORY_LIMIT_REACHED",
    "memory_limit_reached",
    fail_message="This job was terminated because it used more memory than it was allocated.",
    resubmit_description="it exceeded the amount of allocated memory",
    condition="memory_limit_reached",
)
register_runner_state(
    "JOB_OUTPUT_NOT_RETURNED_FROM_CLUSTER",
    "Job output not returned from cluster",
    resubmit_description="its output was not returned from the cluster",
    condition="job_output_not_returned_from_cluster",
)
register_runner_state(
    "UNKNOWN_ERROR",
    "unknown_error",
    fail_message="This job ran into an unknown error.",
    resubmit_description="it encountered an unknown error",
    condition="unknown_error",
)
register_runner_state("GLOBAL_WALLTIME_REACHED", "global_walltime_reached")
register_runner_state(
    "TOOL_TIMELIMIT_REACHED",
    "tool_timelimit_reached",
    resubmit_description="it exceeded the tool's time limit",
    condition="tool_timelimit_reached",
)
register_runner_state("OUTPUT_SIZE_LIMIT", "output_size_limit")
# job runner interaction worked fine but the tool indicated error
register_runner_state(
    "TOOL_DETECT_ERROR",
    "tool_detected",
    resubmit_description="it encountered a tool detected error condition",
    condition="tool_detected_failure",
)
register_runner_state(
    "NODE_FAILURE",
    "node_failure",
    fail_message="This job failed because a node it was running on failed.",
    resubmit_description="a node it was running on failed",
    condition="node_failure",
)
register_runner_state(
    "PREEMPTED",
    "preempted",
    fail_message="This job was stopped because it was preempted by a higher priority job.",
    resubmit_description="it was preempted",
    condition="preempted",
)
# Stopped on purpose by someone outside of Galaxy, so never resubmitted.
register_runner_state(
    "CANCELLED",
    "cancelled",
    fail_message="This job failed because it was cancelled by an administrator.",
)


__all__ = (
    "RUNNER_STATE_DEFINITIONS",
    "RunnerStateDefinition",
    "kill_pid",
    "register_runner_state",
    "runner_states",
)

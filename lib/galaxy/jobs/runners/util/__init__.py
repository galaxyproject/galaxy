"""
This module and its submodules contains utilities for running external
processes and interfacing with job managers. This module should contain
functionality shared between Galaxy and the Pulsar.
"""

from galaxy.util.bunch import Bunch
from .kill import kill_pid

runner_states = Bunch(
    WALLTIME_REACHED="walltime_reached",
    MEMORY_LIMIT_REACHED="memory_limit_reached",
    JOB_OUTPUT_NOT_RETURNED_FROM_CLUSTER="Job output not returned from cluster",
    UNKNOWN_ERROR="unknown_error",
    GLOBAL_WALLTIME_REACHED="global_walltime_reached",
    OUTPUT_SIZE_LIMIT="output_size_limit",
    TOOL_DETECT_ERROR="tool_detected",  # job runner interaction worked fine but the tool indicated error
)


__all__ = (
    "kill_pid",
    "runner_states",
)

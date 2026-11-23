"""
Slurm job state inspection shared between Galaxy and Pulsar.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

from galaxy.util import (
    commands,
    unicodify,
)

log = logging.getLogger(__name__)

NOT_FOUND = "NOT_FOUND"

# Results of check_memory_limit().
MEMORY_LIMIT_EXCEEDED = "exceeded"
MEMORY_LIMIT_PROBABLY_EXCEEDED = "probably_exceeded"

# Error message printed to job stderr when SLURM itself kills a job.
# See src/common/slurm_jobacct_gather.c and src/slurmd/slurmd/req.c in
# https://github.com/SchedMD/slurm/
SLURM_MEMORY_LIMIT_EXCEEDED_MSG = "slurmstepd: error: Exceeded job memory limit"
# Warning messages which may be printed to job stderr by SLURM after termination
# of a job step when using the cgroup task plugin. The exceeded memory is not
# always the cause of the step termination, which can be successful.
# See src/plugins/task/cgroup/task_cgroup_memory.c in
# https://github.com/SchedMD/slurm/
SLURM_MEMORY_LIMIT_EXCEEDED_PARTIAL_WARNINGS = [
    ": Exceeded job memory limit at some point.",
    ": Exceeded step memory limit at some point.",
]


def slurm_job_state(external_id: str, execute: Callable[[list[str]], str] | None = None) -> str:
    """Return the state SLURM reports for a job, or NOT_FOUND if it no longer knows the job."""
    return slurm_job_info(external_id, execute)["JobState"]


def slurm_job_info(external_id: str, execute: Callable[[list[str]], str] | None = None) -> dict[str, str]:
    """Return what SLURM reports about a job, ``JobState`` is NOT_FOUND if it no longer knows the job.

    A job that aged out of ``scontrol`` only has a ``JobState``.
    ``external_id`` may use the slurm-drmaa-with-cluster-support ``job_id.cluster`` syntax.
    """
    execute = execute or commands.execute
    cmd = ["scontrol", "-o"]
    if "." in external_id:
        job_id, cluster = external_id.split(".", 1)
        cmd.extend(["-M", cluster])
    else:
        job_id = external_id
        cluster = None
    cmd.extend(["show", "job", job_id])
    try:
        stdout = execute(cmd).strip()
    except commands.CommandLineException as e:
        if e.stderr == "slurm_load_jobs error: Invalid job id specified\n":
            # The job may be old, try to get its state with sacct
            return {"JobState": _slurm_job_state_with_sacct(job_id, cluster, execute) or NOT_FOUND}
        raise e
    # stdout is a single line in format "key1=value1 key2=value2 ..."
    job_info_keys: list[str] = []
    job_info_values: list[str] = []
    for job_info in stdout.split():
        try:
            # Some value may contain `=` (e.g. `StdIn=StdIn=/dev/null`)
            k, v = job_info.split("=", 1)
            job_info_keys.append(k)
            job_info_values.append(v)
        except ValueError:
            # Some value may contain spaces (e.g. `Comment=** time_limit (60m) min_nodes (1) **`)
            job_info_values[-1] += f" {job_info}"
    return dict(zip(job_info_keys, job_info_values))


def _slurm_job_state_with_sacct(job_id: str, cluster: str | None, execute: Callable[[list[str]], str]) -> str | None:
    cmd = ["sacct", "-n", "-o", "state%-32"]
    if cluster:
        cmd.extend(["-M", cluster])
    cmd.extend(["-j", job_id])
    try:
        stdout = execute(cmd)
    except commands.CommandLineException as e:
        if e.stderr.strip() == "SLURM accounting storage is disabled":
            log.warning("SLURM accounting storage is not properly configured, unable to run sacct")
            return None
        raise e
    # First line is for 'job_id'
    # Second line is for 'job_id.batch' (only available after the batch job is complete)
    # Following lines are for the steps 'job_id.0', 'job_id.1', ... (but Galaxy does not use steps)
    first_line = stdout.splitlines()[0]
    # Strip whitespaces and the final '+' (if present), only return the first word
    return first_line.strip().rstrip("+").split()[0]


def check_memory_limit(efile_path: str) -> str | None:
    """Look for SLURM's exceeded memory messages in the end of a job's stderr file.

    A very poor implementation of tail, but it doesn't need to be fancy since
    we are only searching the last 2K. Returns ``MEMORY_LIMIT_EXCEEDED``,
    ``MEMORY_LIMIT_PROBABLY_EXCEEDED``, or ``None`` if neither message was found.
    """
    try:
        log.debug("Checking %s for exceeded memory message from SLURM", efile_path)
        with open(efile_path, "rb") as f:
            if os.path.getsize(efile_path) > 2048:
                f.seek(-2048, os.SEEK_END)
                f.readline()
            for line in f.readlines():
                stripped_line = unicodify(line.strip())
                if stripped_line == SLURM_MEMORY_LIMIT_EXCEEDED_MSG:
                    return MEMORY_LIMIT_EXCEEDED
                elif any(_ in stripped_line for _ in SLURM_MEMORY_LIMIT_EXCEEDED_PARTIAL_WARNINGS):
                    return MEMORY_LIMIT_PROBABLY_EXCEEDED
    except FileNotFoundError:
        # Entirely expected, this is only called for cancelled jobs
        return None
    except Exception:
        log.exception("Error reading end of %s:", efile_path)
    return None


__all__ = (
    "MEMORY_LIMIT_EXCEEDED",
    "MEMORY_LIMIT_PROBABLY_EXCEEDED",
    "NOT_FOUND",
    "check_memory_limit",
    "slurm_job_info",
    "slurm_job_state",
)

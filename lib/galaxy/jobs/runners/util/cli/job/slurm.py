# A simple CLI runner for slurm that can be used when running Galaxy from a
# non-submit host and using a Slurm cluster.
from __future__ import annotations

import re
from logging import getLogger
from typing import ClassVar

from . import (
    BaseJobExec,
    job_states,
)
from ... import runner_states

log = getLogger(__name__)

argmap = {"time": "-t", "ncpus": "-c", "partition": "-p"}


class Slurm(BaseJobExec):
    slurm_longjobstate_to_shortjobstate: ClassVar[dict[str, str]] = {
        "BOOT_FAIL": "BF",
        "CANCELLED": "CA",
        "COMPLETED": "CD",
        "DEADLINE": "DL",
        "FAILED": "F",
        "NODE_FAIL": "NF",
        "OUT_OF_MEMORY": "OOM",
        "PENDING": "PD",
        "PREEMPTED": "PR",
        "RUNNING": "R",
        "REQUEUED": "RQ",
        "RESIZING": "RS",
        "REVOKED": "RV",
        "SUSPENDED": "S",
        "TIMEOUT": "TO",
        "UNKNOWN": "UN",  # Custom for code in case one isn't available here
    }
    slurmstate_runnerstate_map: ClassVar[dict[str, str]] = {
        "OOM": runner_states.MEMORY_LIMIT_REACHED,
        "TO": runner_states.WALLTIME_REACHED,
        "UN": runner_states.UNKNOWN_ERROR,
        "NF": runner_states.NODE_FAILURE,
        "BF": runner_states.NODE_FAILURE,
        "PR": runner_states.PREEMPTED,
        "CA": runner_states.CANCELLED,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sacct_available = True

    def job_script_kwargs(self, ofile, efile, job_name):
        scriptargs = {"-o": ofile, "-e": efile, "-J": job_name}

        # Map arguments using argmap.
        for k, v in self.params.items():
            if k == "plugin":
                continue
            try:
                if not k.startswith("-"):
                    k = argmap[k]
                scriptargs[k] = v
            except Exception:
                log.warning(f"Unrecognized long argument passed to Slurm CLI plugin: {k}")

        # Generated template.
        template_scriptargs = ""
        for k, v in scriptargs.items():
            template_scriptargs += f"#SBATCH {k} {v}\n"
        return {"headers": template_scriptargs}

    def submit(self, script_file):
        return f"sbatch {script_file}"

    def delete(self, job_id):
        return f"scancel {job_id}"

    def get_status(self, job_ids=None):
        return "squeue -a -o '%A %t'"

    def get_single_status(self, job_id):
        # Without -t all squeue drops a job as soon as it ends, so a job that
        # failed would be indistinguishable from one that succeeded.
        return f"squeue -a -t all -o '%A %t' -j {job_id}"

    def parse_status(self, status, job_ids):
        # Get status for each job, skipping header.
        rval = {}
        for line in status.splitlines()[1:]:
            id, state = line.split()
            if id in job_ids:
                # map job states to Galaxy job states.
                rval[id] = self._get_job_state(state)
        return rval

    def parse_single_status(self, status, job_id, shell):
        status = status.splitlines()
        if len(status) > 1:
            # Job still on cluster and has state.
            _id, state = status[1].split()
            return self._get_job_state(state)
        elif self.sacct_available:
            log.debug(f"For job '{job_id}', relying on 'sacct' method to determine job state")
            # Job no longer on cluster, retrieve state
            pdata = shell.execute(f"sacct -o JobIDRaw,State -P -n -j {job_id}")
            if "Slurm accounting storage is disabled" in pdata.stderr:
                log.warning(f"({job_id}) Slurm accounting storage is disabled")
                self.sacct_available = False

                # Technically we don't know what the state is, but chances are the job just completed very quickly.
                return job_states.OK

            job_data = pdata.stdout.splitlines()

            if len(job_data) == 0:
                log.debug(f"Job '{job_id}' cannot be found. Returning error for job.")
                return self._get_job_state("F")

            return self._get_job_state(self._state_from_sacct(job_data))
        # else line like "slurm_load_jobs error: Invalid job id specified"
        return job_states.OK

    def _state_from_sacct(self, lines):
        state = "CD"
        for line in lines:
            # Ignore the '.batch' and '.extern' in the output
            if ".batch" in line or ".extern" in line:
                continue
            fields = line.split("|")
            if len(fields) >= 2:
                # e.g. "CANCELLED by 1000"
                long_state = fields[1].split(" ", 1)[0]
                state = self.slurm_longjobstate_to_shortjobstate.get(long_state, "UN")
        return state

    def _get_job_state(self, state):
        return {
            "BF": job_states.ERROR,
            "CA": job_states.ERROR,
            "CD": job_states.OK,
            "CG": job_states.RUNNING,
            "DL": job_states.ERROR,
            "F": job_states.ERROR,
            "NF": job_states.ERROR,
            "OOM": job_states.ERROR,
            "PD": job_states.QUEUED,
            "PR": job_states.ERROR,
            "R": job_states.RUNNING,
            "RQ": job_states.RUNNING,
            "RS": job_states.RUNNING,
            "RV": job_states.ERROR,
            "S": job_states.RUNNING,
            "TO": job_states.ERROR,
            "UN": job_states.ERROR,  # Custom code for unknown
        }.get(state)

    def get_failure_reason(self, job_id):
        # scontrol remembers finished jobs for MinJobAge even without accounting,
        # sacct covers jobs that have aged out of it.
        return f"scontrol -o show job {job_id} 2>/dev/null; sacct -o JobIDRaw,State -P -n -j {job_id} 2>/dev/null"

    def parse_failure_reason(self, reason, job_id):
        match = re.search(r"\bJobState=(\S+)", reason)
        if match:
            state = self.slurm_longjobstate_to_shortjobstate.get(match.group(1), "UN")
        else:
            state = self._state_from_sacct(reason.splitlines())
        return self.slurmstate_runnerstate_map.get(state)

    def parse_failure_message(self, reason, job_id):
        match = re.search(r"\bReason=(RaisedSignal\S+)", reason)
        return f"Slurm reported: {match.group(1)}" if match else None


__all__ = ("Slurm",)

# A simple CLI runner for slurm that can be used when running Galaxy from a
# non-submit host and using a Slurm cluster.
from logging import getLogger
import subprocess

from . import (
    BaseJobExec,
    job_states,
)
from ... import runner_states

log = getLogger(__name__)

argmap = {"time": "-t", "ncpus": "-c", "partition": "-p"}


class Slurm(BaseJobExec):
    slurm_longjobstate_to_shortjobstate = {
        'BOOT_FAIL': 'BF',
        'CANCELLED': 'CA',
        'COMPLETED': 'CD',
        'DEADLINE': 'DL',
        'FAILED': 'F',
        'NODE_FAIL': 'NF',
        'OUT_OF_MEMORY': 'OOM',
        'PENDING': 'PD',
        'PREEMPTED': 'PR',
        'RUNNING': 'R',
        'REQUEUED': 'RQ',
        'RESIZING': 'RS',
        'REVOKED': 'RV',
        'SUSPENDED': 'S',
        'TIMEOUT': 'TO',
        'UNKNOWN': 'UN' # Custom for code in case one isn't available here
    }
    slurmstate_runnerstate_map = {
        "OOM": runner_states.MEMORY_LIMIT_REACHED,
        "TO": runner_states.WALLTIME_REACHED,
        "UN": runner_states.UNKNOWN_ERROR
    }

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
        return dict(headers=template_scriptargs)

    def submit(self, script_file):
        return f"sbatch {script_file}"

    def delete(self, job_id):
        return f"scancel {job_id}"

    def get_status(self, job_ids=None):
        return "squeue -a -o '%A %t'"

    def get_single_status(self, job_id):
        return f"squeue -a -o '%A %t' -j {job_id}"

    def parse_status(self, status, job_ids):
        # Get status for each job, skipping header.
        rval = {}
        for line in status.splitlines()[1:]:
            id, state = line.split()
            if id in job_ids:
                # map job states to Galaxy job states.
                rval[id] = self._get_job_state(state)
        return rval

    def parse_single_status(self, status, job_id):
        status = status.splitlines()
        if len(status) > 1:
            # Job still on cluster and has state.
            id, state = status[1].split()
            return self._get_job_state(state)
        elif len(status) <= 1:
            log.debug(f"For job '{job_id}', relying on 'sacct' method to determine job state")
            # Job no longer on cluster, retrieve state
            pdata = subprocess.run(['sacct', '-o', 'JobIDRaw,State', '-P', '-n', '-j', job_id], capture_output=True, encoding='utf-8')
            job_data = pdata.stdout.splitlines()

            if len(job_data) == 0:
                log.debug(f"Job '{job_id}' cannot be found. Returning error for job.")
                return self._get_job_state('F')

            state = "CD"
            for jobline in job_data:
                # Ignore the '.batch' and '.extern' in the output
                if ".batch" in jobline or ".extern" in jobline:
                    continue

                splitjobdata = jobline.split('|')
                if len(splitjobdata) >= 2:
                    (s_jobid, s_jobstate) = splitjobdata
                    if ' ' in s_jobstate:
                        s_jobstate, s_jobotherinfo = s_jobstate.split(' ', 1)
                    state = self.slurm_longjobstate_to_shortjobstate.get(s_jobstate, 'UN')
        # else line like "slurm_load_jobs error: Invalid job id specified"
        return job_states.OK

    def _get_job_state(self, state: str) -> str:
        try:
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
                "PR": job_states.RUNNING,
                "R": job_states.RUNNING,
                "RQ": job_states.RUNNING,
                "RS": job_states.RUNNING,
                "RV": job_states.ERROR,
                "S": job_states.RUNNING,
                "TO": job_states.ERROR,
                "UN": job_states.ERROR # Custom code for unknown
            }.get(state)
        except KeyError:
            raise KeyError(f"Failed to map slurm status code [{state}] to job state.")

    def get_failure_reason(self, job_id):
        return f"sacct -o JobIDRaw,State -P -n -j {job_id}"

    def parse_failure_reason(self, reason, job_id):
        state = "CD"
        for line in reason.splitlines():
            if ".batch" in line or ".extern" in line:
                continue

            splitjobdata = line.split('|')
            log.debug(f"State split line: {len(splitjobdata)}")
            if len(splitjobdata) >= 2:
                (s_jobid, s_jobstate) = splitjobdata
                if ' ' in s_jobstate:
                    s_jobstate, s_jobotherinfo = s_jobstate.split(' ', 1)
                    log.debug(f"Found space in jobstate, split into: {s_jobstate} - {s_jobotherinfo}")
                log.debug(f"State job data: {s_jobid} - {s_jobstate}")
                state = self.slurm_longjobstate_to_shortjobstate.get(s_jobstate, 'UN')

        if state in self.slurmstate_runnerstate_map:
            return self.slurmstate_runnerstate_map.get(state, runner_states.UNKNOWN_ERROR)
        return None


__all__ = ("Slurm",)

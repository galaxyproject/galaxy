# A simple CLI runner for slurm that can be used when running Galaxy from a
# non-submit host and using a Slurm cluster.
from logging import getLogger

from ..job import (
    BaseJobExec,
    job_states,
)

log = getLogger(__name__)

argmap = {"time": "-t", "ncpus": "-c", "partition": "-p"}


class Slurm(BaseJobExec):
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
        # else line like "slurm_load_jobs error: Invalid job id specified"
        return job_states.OK

    def _get_job_state(self, state):
        try:
            return {
                "F": job_states.ERROR,
                "R": job_states.RUNNING,
                "CG": job_states.RUNNING,
                "PD": job_states.QUEUED,
                "CD": job_states.OK,
            }.get(state)
        except KeyError:
            raise KeyError(f"Failed to map slurm status code [{state}] to job state.")


__all__ = ("Slurm",)

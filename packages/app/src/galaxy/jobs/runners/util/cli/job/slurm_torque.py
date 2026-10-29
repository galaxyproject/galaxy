import re

from .torque import Torque

__all__ = ("SlurmTorque",)


class SlurmTorque(Torque):
    """A CLI job executor for Slurm's Torque compatibility mode. This differs
    from real torque CLI in that -x command line is not available so job status
    needs to be parsed from qstat table instead of XML.
    """

    def get_status(self, job_ids=None):
        return "qstat"

    def parse_status(self, status, job_ids):
        rval = {}
        for line in status.strip().splitlines():
            if line.startswith("Job ID"):
                continue
            line_parts = re.compile(r"\s+").split(line)
            if len(line_parts) < 5:
                continue
            id = line_parts[0]
            state = line_parts[4]
            if id in job_ids:
                # map PBS job states to Galaxy job states.
                rval[id] = self._get_job_state(state)
        return rval

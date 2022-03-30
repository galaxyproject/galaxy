import json
from logging import getLogger

from .torque import Torque

log = getLogger(__name__)


class OpenPBS(Torque):

    ERROR_MESSAGE_UNRECOGNIZED_ARG = "Unrecognized long argument passed to OpenPBS CLI plugin: %s"

    def get_status(self, job_ids=None):
        return "qstat -f -F json"

    def get_single_status(self, job_id):
        return f"qstat -f {job_id}"

    def parse_status(self, status, job_ids):
        try:
            data = json.loads(status)
        except Exception:
            log.warning(f"No valid qstat JSON return from `qstat -f -F json`, got the following: {status}")
        rval = {}
        for job_id, job in data.get("Jobs", {}).items():
            if job_id in job_ids:
                # map PBS job states to Galaxy job states.
                rval[id] = self._get_job_state(job["job_state"])
        return rval


__all__ = ("OpenPBS",)

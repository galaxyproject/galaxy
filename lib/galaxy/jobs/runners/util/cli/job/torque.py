from logging import getLogger

from galaxy.util import parse_xml_string
from . import (
    BaseJobExec,
    job_states,
)

log = getLogger(__name__)


argmap = {
    "destination": "-q",
    "Execution_Time": "-a",
    "Account_Name": "-A",
    "Checkpoint": "-c",
    "Error_Path": "-e",
    "Group_List": "-g",
    "Hold_Types": "-h",
    "Join_Paths": "-j",
    "Keep_Files": "-k",
    "Resource_List": "-l",
    "Mail_Points": "-m",
    "Mail_Users": "-M",
    "Job_Name": "-N",
    "Output_Path": "-o",
    "Priority": "-p",
    "Rerunable": "-r",
    "Shell_Path_List": "-S",
    "job_array_request": "-t",
    "User_List": "-u",
    "Variable_List": "-v",
}


class Torque(BaseJobExec):
    ERROR_MESSAGE_UNRECOGNIZED_ARG = "Unrecognized long argument passed to Torque CLI plugin: %s"

    def job_script_kwargs(self, ofile, efile, job_name):
        pbsargs = {"-o": ofile, "-e": efile, "-N": job_name}
        for k, v in self.params.items():
            if k == "plugin":
                continue
            try:
                if not k.startswith("-"):
                    k = argmap[k]
                pbsargs[k] = v
            except KeyError:
                log.warning(self.ERROR_MESSAGE_UNRECOGNIZED_ARG, k)
        template_pbsargs = ""
        for k, v in pbsargs.items():
            template_pbsargs += f"#PBS {k} {v}\n"
        return dict(headers=template_pbsargs)

    def submit(self, script_file):
        return f"qsub {script_file}"

    def delete(self, job_id):
        return f"qdel {job_id}"

    def get_status(self, job_ids=None):
        return "qstat -x"

    def get_single_status(self, job_id):
        return f"qstat -f {job_id}"

    def parse_status(self, status, job_ids):
        # in case there's noise in the output, find the big blob 'o xml
        tree = None
        rval = {}
        for line in status.strip().splitlines():
            try:
                tree = parse_xml_string(line.strip())
                assert tree.tag == "Data"
                break
            except Exception:
                tree = None
        if tree is None:
            log.warning(f"No valid qstat XML return from `qstat -x`, got the following: {status}")
            return {}
        else:
            for job in tree.findall("Job"):
                job_id_elem = job.find("Job_Id")
                assert job_id_elem is not None
                id_ = job_id_elem.text
                if id_ in job_ids:
                    job_state_elem = job.find("job_state")
                    assert job_state_elem is not None
                    state = job_state_elem.text
                    assert state
                    # map PBS job states to Galaxy job states.
                    rval[id_] = self._get_job_state(state)
        return rval

    def parse_single_status(self, status, job_id):
        for line in status.splitlines():
            line = line.split(" = ")
            if line[0].strip() == "job_state":
                return self._get_job_state(line[1].strip())
        # no state found, job has exited
        return job_states.OK

    def _get_job_state(self, state: str) -> job_states:
        try:
            return {"E": job_states.RUNNING, "R": job_states.RUNNING, "Q": job_states.QUEUED, "C": job_states.OK}[state]
        except KeyError:
            raise KeyError(f"Failed to map torque status code [{state}] to job state.")


__all__ = ("Torque",)

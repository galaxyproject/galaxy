"""
SLURM job control via the DRMAA API.
"""

import time
from typing import (
    TYPE_CHECKING,
)

from galaxy import model
from galaxy.jobs.runners.drmaa import DRMAAJobRunner
from galaxy.jobs.runners.util.slurm import (
    check_memory_limit,
    MEMORY_LIMIT_EXCEEDED,
    MEMORY_LIMIT_PROBABLY_EXCEEDED,
    slurm_job_state,
)
from galaxy.util.custom_logging import get_logger

if TYPE_CHECKING:
    from galaxy.jobs.runners.drmaa import DRMAAJobState

log = get_logger(__name__)

__all__ = ("SlurmJobRunner",)

# These messages are returned to the user
OUT_OF_MEMORY_MSG = "This job was terminated because it used more memory than it was allocated."
PROBABLY_OUT_OF_MEMORY_MSG = "This job was cancelled probably because it used more memory than it was allocated."
MEMORY_LIMIT_MESSAGES = {
    MEMORY_LIMIT_EXCEEDED: OUT_OF_MEMORY_MSG,
    MEMORY_LIMIT_PROBABLY_EXCEEDED: PROBABLY_OUT_OF_MEMORY_MSG,
}


class SlurmJobRunner(DRMAAJobRunner):
    runner_name = "SlurmRunner"
    restrict_job_name_length = False

    def _complete_terminal_job(self, ajs: "DRMAAJobState", drmaa_state: str, **kwargs) -> bool | None:
        def _get_slurm_state() -> str:
            assert ajs.job_id is not None
            return slurm_job_state(ajs.job_id)

        try:
            if drmaa_state == self.drmaa_job_states.FAILED:
                slurm_state = _get_slurm_state()
                sleep = 1
                while slurm_state == "COMPLETING":
                    log.debug(
                        "(%s/%s) Waiting %s seconds for failed job to exit COMPLETING state for post-mortem",
                        ajs.job_wrapper.get_id_tag(),
                        ajs.job_id,
                        sleep,
                    )
                    time.sleep(sleep)
                    sleep *= 2
                    if sleep > 64:
                        ajs.fail_message = "This job failed and the system timed out while trying to determine the cause of the failure."
                        break
                    slurm_state = _get_slurm_state()
                if slurm_state == "NOT_FOUND":
                    log.warning(
                        "(%s/%s) Job not found, assuming job check exceeded MinJobAge and completing as successful",
                        ajs.job_wrapper.get_id_tag(),
                        ajs.job_id,
                    )
                    drmaa_state = self.drmaa_job_states.DONE
                elif slurm_state == "COMPLETED":
                    log.debug(
                        "(%s/%s) SLURM reported job success, assuming job check exceeded MinJobAge and completing as successful",
                        ajs.job_wrapper.get_id_tag(),
                        ajs.job_id,
                    )
                    drmaa_state = self.drmaa_job_states.DONE
                elif slurm_state == "TIMEOUT":
                    log.info("(%s/%s) Job hit walltime", ajs.job_wrapper.get_id_tag(), ajs.job_id)
                    ajs.fail_message = (
                        "This job was terminated because it ran longer than the maximum allowed job run time."
                    )
                    ajs.runner_state = ajs.runner_states.WALLTIME_REACHED
                elif slurm_state == "NODE_FAIL":
                    log.warning(
                        "(%s/%s) Job failed due to node failure, attempting resubmission",
                        ajs.job_wrapper.get_id_tag(),
                        ajs.job_id,
                    )
                    self.mark_as_resubmitted(ajs, info="Job was resubmitted due to node failure")
                    return None
                elif slurm_state == "OUT_OF_MEMORY":
                    log.info(
                        "(%s/%s) Job hit memory limit (SLURM state: OUT_OF_MEMORY)",
                        ajs.job_wrapper.get_id_tag(),
                        ajs.job_id,
                    )
                    ajs.fail_message = OUT_OF_MEMORY_MSG
                    ajs.runner_state = ajs.runner_states.MEMORY_LIMIT_REACHED
                elif slurm_state == "CANCELLED":
                    if ajs.job_wrapper.get_state() == model.Job.states.STOPPED:
                        # User requested to stop job, this isn't an error, just finish as normal
                        return super()._complete_terminal_job(ajs, drmaa_state=drmaa_state)
                    # Check to see if the job was killed for exceeding memory consumption
                    memory_limit = check_memory_limit(ajs.error_file)
                    if memory_limit:
                        log.info(
                            "(%s/%s) Job hit memory limit (SLURM state: CANCELLED)",
                            ajs.job_wrapper.get_id_tag(),
                            ajs.job_id,
                        )
                        ajs.fail_message = MEMORY_LIMIT_MESSAGES[memory_limit]
                        ajs.runner_state = ajs.runner_states.MEMORY_LIMIT_REACHED
                    else:
                        log.info(
                            "(%s/%s) Job was cancelled via SLURM (e.g. with scancel(1))",
                            ajs.job_wrapper.get_id_tag(),
                            ajs.job_id,
                        )
                        ajs.fail_message = "This job failed because it was cancelled by an administrator."
                elif slurm_state in ("PENDING", "RUNNING"):
                    log.warning(
                        "(%s/%s) Job was reported by drmaa as terminal but job state in SLURM is: %s, returning to monitor queue",
                        ajs.job_wrapper.get_id_tag(),
                        ajs.job_id,
                        slurm_state,
                    )
                    return True
                else:
                    log.warning(
                        "(%s/%s) Job failed due to unknown reasons, job state in SLURM was: %s",
                        ajs.job_wrapper.get_id_tag(),
                        ajs.job_id,
                        slurm_state,
                    )
                    ajs.fail_message = "This job failed for reasons that could not be determined."
                if drmaa_state == self.drmaa_job_states.FAILED:
                    ajs.fail_message += "\nPlease click the bug icon to report this problem if you need help."
                    ajs.stop_job = False
                    self.work_queue.put((self.fail_job, ajs))
                    return None
        except Exception:
            log.exception(
                "(%s/%s) Failure in SLURM _complete_terminal_job(), job final state will be: %s",
                ajs.job_wrapper.get_id_tag(),
                ajs.job_id,
                drmaa_state,
            )
        # by default, finish the job with the state from drmaa
        return super()._complete_terminal_job(ajs, drmaa_state=drmaa_state)

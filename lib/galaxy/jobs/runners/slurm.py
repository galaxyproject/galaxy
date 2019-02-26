"""
SLURM job control via the DRMAA API.
"""
import os
import re
import shutil
import subprocess
import tempfile
import time

from galaxy import model
from galaxy.jobs.runners.drmaa import DRMAAJobRunner
from galaxy.util.logging import get_logger

log = get_logger(__name__)

__all__ = ('SlurmJobRunner', )

# Error message printed to job stderr when SLURM itself kills a job.
# See src/common/slurm_jobacct_gather.c and src/slurmd/slurmd/req.c in
# https://github.com/SchedMD/slurm/
SLURM_MEMORY_LIMIT_EXCEEDED_MSG = 'slurmstepd: error: Exceeded job memory limit'
# Warning messages which may be printed to job stderr by SLURM after termination
# of a job step when using the cgroup task plugin. The exceeded memory is not
# always the cause of the step termination, which can be successful.
# See src/plugins/task/cgroup/task_cgroup_memory.c in
# https://github.com/SchedMD/slurm/
SLURM_MEMORY_LIMIT_EXCEEDED_PARTIAL_WARNINGS = [': Exceeded job memory limit at some point.',
                                                ': Exceeded step memory limit at some point.']
SLURM_MEMORY_LIMIT_SCAN_SIZE = 16 * 1024 * 1024  # 16MB
SLURM_UNABLE_TO_ADD_TASK_TO_MEMORY_CG_MSG_RE = re.compile(r"""slurmstepd: error: task/cgroup: unable to add task\[pid=\d+\] to memory cg '\(null\)'$""")
SLURM_UNABLE_TO_CREATE_CGROUP_MSG_RE = re.compile(r"""slurmstepd: error: xcgroup_instantiate: unable to create cgroup '[^']+' : No space left on device$""")
SLURM_UNABLE_TO_INSTANCIATE_JOB_MSG_RE = re.compile(r"""slurmstepd: error: jobacct_gather/cgroup: unable to instanciate job \d+ memory cgroup$""")
SLURM_TOP_WARNING_RES = (
    SLURM_UNABLE_TO_ADD_TASK_TO_MEMORY_CG_MSG_RE,
    SLURM_UNABLE_TO_CREATE_CGROUP_MSG_RE,
    SLURM_UNABLE_TO_INSTANCIATE_JOB_MSG_RE
)

# These messages are returned to the user
OUT_OF_MEMORY_MSG = 'This job was terminated because it used more memory than it was allocated.'
PROBABLY_OUT_OF_MEMORY_MSG = 'This job was cancelled probably because it used more memory than it was allocated.'


class SlurmJobRunner(DRMAAJobRunner):
    runner_name = "SlurmRunner"
    restrict_job_name_length = False

    def _complete_terminal_job(self, ajs, drmaa_state, **kwargs):
        def _get_slurm_state_with_sacct(job_id, cluster):
            cmd = ['sacct', '-n', '-o', 'state%-32']
            if cluster:
                cmd.extend(['-M', cluster])
            cmd.extend(['-j', job_id])
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                stderr = stderr.strip()
                if stderr == 'SLURM accounting storage is disabled':
                    log.warning('SLURM accounting storage is not properly configured, unable to run sacct')
                    return
                raise Exception('`%s` returned %s, stderr: %s' % (' '.join(cmd), p.returncode, stderr))
            # First line is for 'job_id'
            # Second line is for 'job_id.batch' (only available after the batch job is complete)
            # Following lines are for the steps 'job_id.0', 'job_id.1', ... (but Galaxy does not use steps)
            first_line = stdout.splitlines()[0]
            # Strip whitespaces and the final '+' (if present), only return the first word
            return first_line.strip().rstrip('+').split()[0]

        def _get_slurm_state():
            cmd = ['scontrol', '-o']
            if '.' in ajs.job_id:
                # custom slurm-drmaa-with-cluster-support job id syntax
                job_id, cluster = ajs.job_id.split('.', 1)
                cmd.extend(['-M', cluster])
            else:
                job_id = ajs.job_id
                cluster = None
            cmd.extend(['show', 'job', job_id])
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                # Will need to be more clever here if this message is not consistent
                if stderr == 'slurm_load_jobs error: Invalid job id specified\n':
                    # The job may be old, try to get its state with sacct
                    job_state = _get_slurm_state_with_sacct(job_id, cluster)
                    if job_state:
                        return job_state
                    return 'NOT_FOUND'
                raise Exception('`%s` returned %s, stderr: %s' % (' '.join(cmd), p.returncode, stderr))
            stdout = stdout.strip()
            # stdout is a single line in format "key1=value1 key2=value2 ..."
            job_info_keys = []
            job_info_values = []
            for job_info in stdout.split():
                try:
                    # Some value may contain `=` (e.g. `StdIn=StdIn=/dev/null`)
                    k, v = job_info.split('=', 1)
                    job_info_keys.append(k)
                    job_info_values.append(v)
                except ValueError:
                    # Some value may contain spaces (e.g. `Comment=** time_limit (60m) min_nodes (1) **`)
                    job_info_values[-1] += ' ' + job_info
            job_info_dict = dict(zip(job_info_keys, job_info_values))
            return job_info_dict['JobState']

        try:
            if drmaa_state == self.drmaa_job_states.FAILED:
                slurm_state = _get_slurm_state()
                sleep = 1
                while slurm_state == 'COMPLETING':
                    log.debug('(%s/%s) Waiting %s seconds for failed job to exit COMPLETING state for post-mortem', ajs.job_wrapper.get_id_tag(), ajs.job_id, sleep)
                    time.sleep(sleep)
                    sleep *= 2
                    if sleep > 64:
                        ajs.fail_message = "This job failed and the system timed out while trying to determine the cause of the failure."
                        break
                    slurm_state = _get_slurm_state()
                if slurm_state == 'NOT_FOUND':
                    log.warning('(%s/%s) Job not found, assuming job check exceeded MinJobAge and completing as successful', ajs.job_wrapper.get_id_tag(), ajs.job_id)
                    drmaa_state = self.drmaa_job_states.DONE
                elif slurm_state == 'COMPLETED':
                    log.debug("(%s/%s) SLURM reported job success, assuming job check exceeded MinJobAge and completing as successful", ajs.job_wrapper.get_id_tag(), ajs.job_id)
                    drmaa_state = self.drmaa_job_states.DONE
                elif slurm_state == 'TIMEOUT':
                    log.info('(%s/%s) Job hit walltime', ajs.job_wrapper.get_id_tag(), ajs.job_id)
                    ajs.fail_message = "This job was terminated because it ran longer than the maximum allowed job run time."
                    ajs.runner_state = ajs.runner_states.WALLTIME_REACHED
                elif slurm_state == 'NODE_FAIL':
                    log.warning('(%s/%s) Job failed due to node failure, attempting resubmission', ajs.job_wrapper.get_id_tag(), ajs.job_id)
                    ajs.job_wrapper.change_state(model.Job.states.QUEUED, info='Job was resubmitted due to node failure')
                    try:
                        self.queue_job(ajs.job_wrapper)
                        return
                    except Exception:
                        ajs.fail_message = "This job failed due to a cluster node failure, and an attempt to resubmit the job failed."
                elif slurm_state == 'OUT_OF_MEMORY':
                    log.info('(%s/%s) Job hit memory limit (SLURM state: OUT_OF_MEMORY)', ajs.job_wrapper.get_id_tag(), ajs.job_id)
                    ajs.fail_message = OUT_OF_MEMORY_MSG
                    ajs.runner_state = ajs.runner_states.MEMORY_LIMIT_REACHED
                elif slurm_state == 'CANCELLED':
                    # Check to see if the job was killed for exceeding memory consumption
                    check_memory_limit_msg = self.__check_memory_limit(ajs.error_file)
                    if check_memory_limit_msg:
                        log.info('(%s/%s) Job hit memory limit (SLURM state: CANCELLED)', ajs.job_wrapper.get_id_tag(), ajs.job_id)
                        ajs.fail_message = check_memory_limit_msg
                        ajs.runner_state = ajs.runner_states.MEMORY_LIMIT_REACHED
                    else:
                        log.info('(%s/%s) Job was cancelled via SLURM (e.g. with scancel(1))', ajs.job_wrapper.get_id_tag(), ajs.job_id)
                        ajs.fail_message = "This job failed because it was cancelled by an administrator."
                elif slurm_state in ('PENDING', 'RUNNING'):
                    log.warning('(%s/%s) Job was reported by drmaa as terminal but job state in SLURM is: %s, returning to monitor queue', ajs.job_wrapper.get_id_tag(), ajs.job_id, slurm_state)
                    return True
                else:
                    log.warning('(%s/%s) Job failed due to unknown reasons, job state in SLURM was: %s', ajs.job_wrapper.get_id_tag(), ajs.job_id, slurm_state)
                    ajs.fail_message = "This job failed for reasons that could not be determined."
                if drmaa_state == self.drmaa_job_states.FAILED:
                    ajs.fail_message += '\nPlease click the bug icon to report this problem if you need help.'
                    ajs.stop_job = False
                    self.work_queue.put((self.fail_job, ajs))
                    return
            if drmaa_state == self.drmaa_job_states.DONE:
                with open(ajs.error_file, 'r') as rfh:
                    _remove_spurious_top_lines(rfh, ajs)
                with open(ajs.error_file, 'r+') as f:
                    if os.path.getsize(ajs.error_file) > SLURM_MEMORY_LIMIT_SCAN_SIZE:
                        f.seek(-SLURM_MEMORY_LIMIT_SCAN_SIZE, os.SEEK_END)
                        f.readline()
                    pos = f.tell()
                    lines = f.readlines()
                    f.seek(pos)
                    for line in lines:
                        stripped_line = line.strip()
                        if any(_ in stripped_line for _ in SLURM_MEMORY_LIMIT_EXCEEDED_PARTIAL_WARNINGS):
                            log.debug('(%s/%s) Job completed, removing SLURM exceeded memory warning: "%s"', ajs.job_wrapper.get_id_tag(), ajs.job_id, stripped_line)
                        else:
                            f.write(line)
                    f.truncate()
        except Exception:
            log.exception('(%s/%s) Failure in SLURM _complete_terminal_job(), job final state will be: %s', ajs.job_wrapper.get_id_tag(), ajs.job_id, drmaa_state)
        # by default, finish the job with the state from drmaa
        return super(SlurmJobRunner, self)._complete_terminal_job(ajs, drmaa_state=drmaa_state)

    def __check_memory_limit(self, efile_path):
        """
        A very poor implementation of tail, but it doesn't need to be fancy
        since we are only searching the last 2K
        """
        try:
            log.debug('Checking %s for exceeded memory message from SLURM', efile_path)
            with open(efile_path) as f:
                if os.path.getsize(efile_path) > 2048:
                    f.seek(-2048, os.SEEK_END)
                    f.readline()
                for line in f.readlines():
                    stripped_line = line.strip()
                    if stripped_line == SLURM_MEMORY_LIMIT_EXCEEDED_MSG:
                        return OUT_OF_MEMORY_MSG
                    elif any(_ in stripped_line for _ in SLURM_MEMORY_LIMIT_EXCEEDED_PARTIAL_WARNINGS):
                        return PROBABLY_OUT_OF_MEMORY_MSG
        except Exception:
            log.exception('Error reading end of %s:', efile_path)

        return False


def _remove_spurious_top_lines(rfh, ajs, maxlines=3):
    bad = []
    putback = None
    for i in range(maxlines):
        line = rfh.readline()
        log.trace('checking line: %s', line)
        for pattern in SLURM_TOP_WARNING_RES:
            if pattern.match(line):
                bad.append(line)
                # found a match, stop checking REs and check next line
                break
        else:
            if bad:
                # no match found on this line so line is now a good line, but previous bad lines are found, so it needs to be put back
                putback = line
            # no match on this line, stop looking
            break
        # check next line
    if bad:
        with tempfile.NamedTemporaryFile('w', delete=False) as wfh:
            if putback is not None:
                wfh.write(putback)
            shutil.copyfileobj(rfh, wfh)
            wf_name = wfh.name
        shutil.move(wf_name, ajs.error_file)
        for line in bad:
            log.debug('(%s/%s) Job completed, removing SLURM spurious warning: "%s"', ajs.job_wrapper.get_id_tag(), ajs.job_id, line)

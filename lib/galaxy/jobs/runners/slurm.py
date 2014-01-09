"""
SLURM job control via the DRMAA API.
"""

import time
import logging
import subprocess

from galaxy import model
from galaxy.jobs.runners.drmaa import DRMAAJobRunner

log = logging.getLogger( __name__ )

__all__ = [ 'SlurmJobRunner' ]


class SlurmJobRunner( DRMAAJobRunner ):
    runner_name = "SlurmRunner"

    def _complete_terminal_job( self, ajs, drmaa_state, **kwargs ):
        def __get_jobinfo():
            scontrol_out = subprocess.check_output( ( 'scontrol', '-o', 'show', 'job', ajs.job_id ) )
            return dict( [ out_param.split( '=', 1 ) for out_param in scontrol_out.split() ] )
        if drmaa_state == self.drmaa_job_states.FAILED:
            try:
                job_info = __get_jobinfo()
                sleep = 1
                while job_info['JobState'] == 'COMPLETING':
                    log.debug( '(%s/%s) Waiting %s seconds for failed job to exit COMPLETING state for post-mortem', ajs.job_wrapper.get_id_tag(), ajs.job_id, sleep )
                    time.sleep( sleep )
                    sleep *= 2
                    if sleep > 64:
                        ajs.fail_message = "This job failed and the system timed out while trying to determine the cause of the failure."
                        break
                    job_info = __get_jobinfo()
                if job_info['JobState'] == 'TIMEOUT':
                    ajs.fail_message = "This job was terminated because it ran longer than the maximum allowed job run time."
                elif job_info['JobState'] == 'NODE_FAIL':
                    log.warning( '(%s/%s) Job failed due to node failure, attempting resubmission', ajs.job_wrapper.get_id_tag(), ajs.job_id )
                    ajs.job_wrapper.change_state( model.Job.states.QUEUED, info = 'Job was resubmitted due to node failure' )
                    try:
                        self.queue_job( ajs.job_wrapper )
                        return
                    except:
                        ajs.fail_message = "This job failed due to a cluster node failure, and an attempt to resubmit the job failed."
                elif job_info['JobState'] == 'CANCELLED':
                    ajs.fail_message = "This job failed because it was cancelled by an administrator."
                else:
                    ajs.fail_message = "This job failed for reasons that could not be determined."
                ajs.fail_message += '\nPlease click the bug icon to report this problem if you need help.'
                ajs.stop_job = False
                self.work_queue.put( ( self.fail_job, ajs ) )
            except Exception, e:
                log.exception( '(%s/%s) Unable to inspect failed slurm job using scontrol, job will be unconditionally failed: %s', ajs.job_wrapper.get_id_tag(), ajs.job_id, e )
                super( SlurmJobRunner, self )._complete_terminal_job( ajs, drmaa_state = drmaa_state )
        elif drmaa_state == self.drmaa_job_states.DONE:
            super( SlurmJobRunner, self )._complete_terminal_job( ajs, drmaa_state = drmaa_state )

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

SLURM_MEMORY_LIMIT_EXCEEDED_MSG = 'slurmstepd: error: Exceeded job memory limit'


class SlurmJobRunner( DRMAAJobRunner ):
    runner_name = "SlurmRunner"

    def _complete_terminal_job( self, ajs, drmaa_state, **kwargs ):
        def __get_jobinfo():
            job_id = ajs.job_id
            cmd = [ 'scontrol', '-o' ]
            if '.' in ajs.job_id:
                # custom slurm-drmaa-with-cluster-support job id syntax
                job_id, cluster = ajs.job_id.split('.', 1)
                cmd.extend( [ '-M', cluster ] )
            cmd.extend( [ 'show', 'job', job_id ] )
            p = subprocess.Popen( cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                # Will need to be more clever here if this message is not consistent
                if stderr == 'slurm_load_jobs error: Invalid job id specified\n':
                    return dict( JobState='NOT_FOUND' )
                raise Exception( '`%s` returned %s, stderr: %s' % ( ' '.join( cmd ), p.returncode, stderr ) )
            return dict( [ out_param.split( '=', 1 ) for out_param in stdout.split() ] )
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
                if job_info['JobState'] == 'NOT_FOUND':
                    log.warning( '(%s/%s) Job not found, assuming job check exceeded MinJobAge and completing as successful', ajs.job_wrapper.get_id_tag(), ajs.job_id )
                    drmaa_state = self.drmaa_job_states.DONE
                elif job_info['JobState'] == 'TIMEOUT':
                    log.info( '(%s/%s) Job hit walltime', ajs.job_wrapper.get_id_tag(), ajs.job_id )
                    ajs.fail_message = "This job was terminated because it ran longer than the maximum allowed job run time."
                    ajs.runner_state = ajs.runner_states.WALLTIME_REACHED
                elif job_info['JobState'] == 'NODE_FAIL':
                    log.warning( '(%s/%s) Job failed due to node failure, attempting resubmission', ajs.job_wrapper.get_id_tag(), ajs.job_id )
                    ajs.job_wrapper.change_state( model.Job.states.QUEUED, info='Job was resubmitted due to node failure' )
                    try:
                        self.queue_job( ajs.job_wrapper )
                        return
                    except:
                        ajs.fail_message = "This job failed due to a cluster node failure, and an attempt to resubmit the job failed."
                elif job_info['JobState'] == 'CANCELLED':
                    # Check to see if the job was killed for exceeding memory consumption
                    if self.__check_memory_limit( ajs.error_file ):
                        log.info( '(%s/%s) Job hit memory limit', ajs.job_wrapper.get_id_tag(), ajs.job_id )
                        ajs.fail_message = "This job was terminated because it used more memory than it was allocated."
                        ajs.runner_state = ajs.runner_states.MEMORY_LIMIT_REACHED
                    else:
                        log.info( '(%s/%s) Job was cancelled via slurm (e.g. with scancel(1))', ajs.job_wrapper.get_id_tag(), ajs.job_id )
                        ajs.fail_message = "This job failed because it was cancelled by an administrator."
                else:
                    log.warning( '(%s/%s) Job failed due to unknown reasons, JobState was: %s', ajs.job_wrapper.get_id_tag(), ajs.job_id, job_info['JobState'] )
                    ajs.fail_message = "This job failed for reasons that could not be determined."
                if drmaa_state == self.drmaa_job_states.FAILED:
                    ajs.fail_message += '\nPlease click the bug icon to report this problem if you need help.'
                    ajs.stop_job = False
                    self.work_queue.put( ( self.fail_job, ajs ) )
                    return
            except Exception as e:
                log.exception( '(%s/%s) Unable to inspect failed slurm job using scontrol, job will be unconditionally failed: %s', ajs.job_wrapper.get_id_tag(), ajs.job_id, e )
                super( SlurmJobRunner, self )._complete_terminal_job( ajs, drmaa_state=drmaa_state )
        # by default, finish as if the job was successful.
        super( SlurmJobRunner, self )._complete_terminal_job( ajs, drmaa_state=drmaa_state )

    def __check_memory_limit( self, efile_path ):
        """
        A very poor implementation of tail, but it doesn't need to be fancy
        since we are only searching the last 2K
        """
        try:
            log.debug( 'Checking %s for exceeded memory message from slurm', efile_path )
            with open( efile_path ) as f:
                pos = 2
                bof = False
                while pos < 2048:
                    try:
                        f.seek(-pos, 2)
                        pos += 1
                    except:
                        f.seek(-pos + 1, 2)
                        bof = True

                    if (bof or f.read(1) == '\n') and f.readline().strip() == SLURM_MEMORY_LIMIT_EXCEEDED_MSG:
                        return True

                    if bof:
                        break
        except:
            log.exception('Error reading end of %s:', efile_path)

        return False

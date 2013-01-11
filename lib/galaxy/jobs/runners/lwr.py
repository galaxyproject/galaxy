import logging
import subprocess

from galaxy import model
from galaxy.jobs.runners import ClusterJobState, ClusterJobRunner

import errno
from time import sleep

from lwr_client import FileStager, Client

log = logging.getLogger( __name__ )

__all__ = [ 'LwrJobRunner' ]


class LwrJobRunner( ClusterJobRunner ):
    """
    LWR Job Runner
    """
    runner_name = "LWRRunner"

    def __init__( self, app ):
        """Start the job runner """
        super( LwrJobRunner, self ).__init__( app )
        self._init_monitor_thread()
        log.info( "starting LWR workers" )
        self._init_worker_threads()

    def check_watched_item(self, job_state):
        try:
            client = self.get_client_from_state(job_state)
            complete = client.check_complete()
        except Exception:
            # An orphaned job was put into the queue at app startup, so remote server went down
            # either way we are done I guess.
            self.mark_as_finished(job_state)
            return None
        if complete:
            self.mark_as_finished(job_state)
            return None
        return job_state

    def queue_job(self, job_wrapper):
        stderr = stdout = command_line = ''

        runner_url = job_wrapper.get_job_runner_url()

        try:
            job_wrapper.prepare()
            if hasattr(job_wrapper, 'prepare_input_files_cmds') and job_wrapper.prepare_input_files_cmds is not None:
                for cmd in job_wrapper.prepare_input_files_cmds: # run the commands to stage the input files
                    #log.debug( 'executing: %s' % cmd )
                    if 0 != os.system(cmd):
                        raise Exception('Error running file staging command: %s' % cmd)
                job_wrapper.prepare_input_files_cmds = None # prevent them from being used in-line
            command_line = self.build_command_line( job_wrapper, include_metadata=False, include_work_dir_outputs=False )
        except:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        # If we were able to get a command line, run the job
        if not command_line:
            job_wrapper.finish( '', '' )
            return

        try:
            #log.debug( 'executing: %s' % command_line )
            client = self.get_client_from_wrapper(job_wrapper)
            output_files = self.get_output_files(job_wrapper)
            input_files = job_wrapper.get_input_fnames()
            working_directory = job_wrapper.working_directory
            file_stager = FileStager(client, command_line, job_wrapper.extra_filenames, input_files, output_files, job_wrapper.tool.tool_dir, working_directory)
            rebuilt_command_line = file_stager.get_rewritten_command_line()
            client.launch( rebuilt_command_line )
            job_wrapper.set_runner( runner_url, job_wrapper.job_id )
            job_wrapper.change_state( model.Job.states.RUNNING )

        except Exception, exc:
            job_wrapper.fail( "failure running job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        lwr_job_state = ClusterJobState()
        lwr_job_state.job_wrapper = job_wrapper
        lwr_job_state.job_id = job_wrapper.job_id
        lwr_job_state.old_state = True
        lwr_job_state.running = True
        lwr_job_state.runner_url = runner_url
        self.monitor_job(lwr_job_state)

    def get_output_files(self, job_wrapper):
        output_fnames = job_wrapper.get_output_fnames()
        return [ str( o ) for o in output_fnames ]


    def determine_lwr_url(self, url):
        lwr_url = url[ len( 'lwr://' ) : ]
        return  lwr_url 

    def get_client_from_wrapper(self, job_wrapper):
        job_id = job_wrapper.job_id
        if hasattr(job_wrapper, 'task_id'):
            job_id = "%s_%s" % (job_id, job_wrapper.task_id)
        return self.get_client( job_wrapper.get_job_runner_url(), job_id )

    def get_client_from_state(self, job_state):
        job_runner = job_state.runner_url
        job_id = job_state.job_id
        return self.get_client(job_runner, job_id)

    def get_client(self, job_runner, job_id):
        lwr_url = self.determine_lwr_url( job_runner )
        return Client(lwr_url, job_id)   

    def finish_job( self, job_state ):
        stderr = stdout = command_line = ''
        job_wrapper = job_state.job_wrapper
        try:
            client = self.get_client_from_state(job_state)

            run_results = client.raw_check_complete()
            log.debug('run_results %s' % run_results )
            stdout = run_results['stdout']
            stderr = run_results['stderr']

            if job_wrapper.get_state() not in [ model.Job.states.ERROR, model.Job.states.DELETED ]:
                work_dir_outputs = self.get_work_dir_outputs(job_wrapper)
                output_files = self.get_output_files(job_wrapper)
                for source_file, output_file in work_dir_outputs:
                    client.download_work_dir_output(source_file, job_wrapper.working_directory, output_file)
                    # Remove from full output_files list so don't try to download directly.
                    output_files.remove(output_file)
                for output_file in output_files:
                    client.download_output(output_file, working_directory=job_wrapper.working_directory)
            client.clean()
            log.debug('execution finished: %s' % command_line)
        except Exception, exc:
            job_wrapper.fail( "failure running job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return
        #run the metadata setting script here
        #this is terminate-able when output dataset/job is deleted
        #so that long running set_meta()s can be canceled without having to reboot the server
        if job_wrapper.get_state() not in [ model.Job.states.ERROR, model.Job.states.DELETED ] and self.app.config.set_metadata_externally and job_wrapper.output_paths:
            external_metadata_script = job_wrapper.setup_external_metadata( output_fnames = job_wrapper.get_output_fnames(),
                                                                            set_extension = True,
                                                                            kwds = { 'overwrite' : False } ) #we don't want to overwrite metadata that was copied over in init_meta(), as per established behavior
            log.debug( 'executing external set_meta script for job %d: %s' % ( job_wrapper.job_id, external_metadata_script ) )
            external_metadata_proc = subprocess.Popen( args = external_metadata_script, 
                                         shell = True, 
                                         env = os.environ,
                                         preexec_fn = os.setpgrp )
            job_wrapper.external_output_metadata.set_job_runner_external_pid( external_metadata_proc.pid, self.sa_session )
            external_metadata_proc.wait()
            log.debug( 'execution of external set_meta finished for job %d' % job_wrapper.job_id )

        # Finish the job                
        try:
            job_wrapper.finish( stdout, stderr )
        except:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

    def fail_job( self, job_state ):
        """
        Seperated out so we can use the worker threads for it.
        """
        self.stop_job( self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id ) )
        job_state.job_wrapper.fail( job_state.fail_message )

    def shutdown( self ):
        """Attempts to gracefully shut down the worker threads"""
        log.info( "sending stop signal to worker threads" )
        for i in range( len( self.threads ) ):
            self.queue.put( self.STOP_SIGNAL )
        log.info( "local job runner stopped" )

    def check_pid( self, pid ):
        try:
            os.kill( pid, 0 )
            return True
        except OSError, e:
            if e.errno == errno.ESRCH:
                log.debug( "check_pid(): PID %d is dead" % pid )
            else:
                log.warning( "check_pid(): Got errno %s when attempting to check PID %d: %s" %( errno.errorcode[e.errno], pid, e.strerror ) )
            return False

    def stop_job( self, job ):
        #if our local job has JobExternalOutputMetadata associated, then our primary job has to have already finished
        job_ext_output_metadata = job.get_external_output_metadata()
        if job_ext_output_metadata: 
            pid = job_ext_output_metadata[0].job_runner_external_pid #every JobExternalOutputMetadata has a pid set, we just need to take from one of them
            if pid in [ None, '' ]:
                log.warning( "stop_job(): %s: no PID in database for job, unable to stop" % job.id )
                return
            pid = int( pid )
            if not self.check_pid( pid ):
                log.warning( "stop_job(): %s: PID %d was already dead or can't be signaled" % ( job.id, pid ) )
                return
            for sig in [ 15, 9 ]:
                try:
                    os.killpg( pid, sig )
                except OSError, e:
                    log.warning( "stop_job(): %s: Got errno %s when attempting to signal %d to PID %d: %s" % ( job.id, errno.errorcode[e.errno], sig, pid, e.strerror ) )
                    return  # give up
                sleep( 2 )
                if not self.check_pid( pid ):
                    log.debug( "stop_job(): %s: PID %d successfully killed with signal %d" %( job.id, pid, sig ) )
                    return
                else:
                    log.warning( "stop_job(): %s: PID %d refuses to die after signaling TERM/KILL" %( job.id, pid ) )
        else:
            # Remote kill
            lwr_url = job.job_runner_name
            job_id = job.job_runner_external_id
            log.debug("Attempt remote lwr kill of job with url %s and id %s" % (lwr_url, job_id))
            client = self.get_client(lwr_url, job_id)
            client.kill()


    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_state = ClusterJobState()
        job_state.job_id = str( job.get_job_runner_external_id() )
        job_state.runner_url = job_wrapper.get_job_runner_url()
        job_wrapper.command_line = job.get_command_line()
        job_state.job_wrapper = job_wrapper
        if job.get_state() == model.Job.states.RUNNING:
            log.debug( "(LWR/%s) is still in running state, adding to the LWR queue" % ( job.get_id()) )
            job_state.old_state = True
            job_state.running = True
            self.monitor_queue.put( job_state )
        elif job.get_state() == model.Job.states.QUEUED:
            # LWR doesn't queue currently, so this indicates galaxy was shutoff while 
            # job was being staged. Not sure how to recover from that. 
            job_state.job_wrapper.fail( "This job was killed when Galaxy was restarted.  Please retry the job." )

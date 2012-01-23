import logging
import subprocess
import tempfile
from Queue import Queue
import threading

from galaxy import model
from galaxy.datatypes.data import nice_size
from galaxy.jobs.runners import BaseJobRunner

import os, errno
from time import sleep

log = logging.getLogger( __name__ )

__all__ = [ 'LocalJobRunner' ]

class LocalJobRunner( BaseJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Start the job runner with 'nworkers' worker threads"""
        self.app = app
        self.sa_session = app.model.context
        # put lib into the PYTHONPATH for subprocesses
        if 'PYTHONPATH' in os.environ:
            os.environ['PYTHONPATH'] = '%s:%s' % ( os.environ['PYTHONPATH'], os.path.abspath( 'lib' ) )
        else:
            os.environ['PYTHONPATH'] = os.path.abspath( 'lib' )
        # start workers
        self.queue = Queue()
        self.threads = []
        nworkers = app.config.local_job_queue_workers
        log.info( "starting workers" )
        for i in range( nworkers  ):
            worker = threading.Thread( target=self.run_next )
            worker.start()
            self.threads.append( worker )
        log.debug( "%d workers ready", nworkers )

    def run_next( self ):
        """Run the next job, waiting until one is available if neccesary"""
        while 1:
            job_wrapper = self.queue.get()
            if job_wrapper is self.STOP_SIGNAL:
                return
            try:
                self.run_job( job_wrapper )
            except:
                log.exception( "Uncaught exception running job" )
                
    def run_job( self, job_wrapper ):
        job_wrapper.set_runner( 'local:///', None )
        stderr = stdout = command_line = ''
        # Prepare the job to run
        try:
            job_wrapper.prepare()
            command_line = self.build_command_line( job_wrapper )
        except:
            log.exception("failure running job %d" % job_wrapper.job_id)
            job_wrapper.fail( "failure preparing job", exception=True )
            return
        # If we were able to get a command line, run the job
        if command_line:
            try:
                log.debug( 'executing: %s' % command_line )
                stdout_file = tempfile.NamedTemporaryFile( suffix='_stdout', dir=job_wrapper.working_directory )
                stderr_file = tempfile.NamedTemporaryFile( suffix='_stderr', dir=job_wrapper.working_directory )
                proc = subprocess.Popen( args = command_line, 
                                         shell = True, 
                                         cwd = job_wrapper.working_directory, 
                                         stdout = stdout_file,
                                         stderr = stderr_file,
                                         env = os.environ,
                                         preexec_fn = os.setpgrp )
                job_wrapper.set_runner( 'local:///', proc.pid )
                job_wrapper.change_state( model.Job.states.RUNNING )
                if self.app.config.output_size_limit > 0:
                    sleep_time = 1
                    while proc.poll() is None:
                        for outfile, size in job_wrapper.check_output_sizes():
                            if size > self.app.config.output_size_limit:
                                # Error the job immediately
                                job_wrapper.fail( 'Job output grew too large (greater than %s), please try different job parameters or' \
                                    % nice_size( self.app.config.output_size_limit ) )
                                log.warning( 'Terminating job %s due to output %s growing larger than %s limit' \
                                    % ( job_wrapper.job_id, os.path.basename( outfile ), nice_size( self.app.config.output_size_limit ) ) )
                                # Then kill it
                                os.killpg( proc.pid, 15 )
                                sleep( 1 )
                                if proc.poll() is None:
                                    os.killpg( proc.pid, 9 )
                                proc.wait() # reap
                                log.debug( 'Job %s (pid %s) terminated' % ( job_wrapper.job_id, proc.pid ) )
                                return
                            sleep( sleep_time )
                            if sleep_time < 8:
                                # So we don't stat every second
                                sleep_time *= 2
                proc.wait() # reap
                stdout_file.seek( 0 )
                stderr_file.seek( 0 )
                stdout = stdout_file.read( 32768 )
                stderr = stderr_file.read( 32768 )
                stdout_file.close()
                stderr_file.close()
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
                                                                            tmp_dir = job_wrapper.working_directory,
                                                                            kwds = { 'overwrite' : False } ) #we don't want to overwrite metadata that was copied over in init_meta(), as per established behavior
            log.debug( 'executing external set_meta script for job %d: %s' % ( job_wrapper.job_id, external_metadata_script ) )
            external_metadata_proc = subprocess.Popen( args = external_metadata_script, 
                                         shell = True, 
                                         env = os.environ,
                                         preexec_fn = os.setpgrp )
            job_wrapper.external_output_metadata.set_job_runner_external_pid( external_metadata_proc.pid, self.sa_session )
            external_metadata_proc.wait()
            log.debug( 'execution of external set_meta for job %d finished' % job_wrapper.job_id )
        
        # Finish the job                
        try:
            job_wrapper.finish( stdout, stderr )
        except:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

    def put( self, job_wrapper ):
        """Add a job to the queue (by job identifier)"""
        # Change to queued state before handing to worker thread so the runner won't pick it up again
        job_wrapper.change_state( model.Job.states.QUEUED )
        self.queue.put( job_wrapper )
    
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
        if job.external_output_metadata:
            pid = job.external_output_metadata[0].job_runner_external_pid #every JobExternalOutputMetadata has a pid set, we just need to take from one of them
        else:
            pid = job.job_runner_external_id
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

    def recover( self, job, job_wrapper ):
        # local jobs can't be recovered
        job_wrapper.change_state( model.Job.states.ERROR, info = "This job was killed when Galaxy was restarted.  Please retry the job." )


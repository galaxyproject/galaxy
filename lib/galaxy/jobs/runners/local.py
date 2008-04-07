import logging
import subprocess
from Queue import Queue
import threading

from galaxy import model

import os, errno
from time import sleep

log = logging.getLogger( __name__ )

class LocalJobRunner( object ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Start the job runner with 'nworkers' worker threads"""
        self.app = app
        self.queue = Queue()
        self.threads = []
        nworkers = app.config.job_queue_workers
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
        job_wrapper.change_state( 'running' )
        job_wrapper.set_runner( 'local:///', None )
        stderr = stdout = command_line = ''
        # Prepare the job to run
        try:
            job_wrapper.prepare()
            command_line = job_wrapper.get_command_line()
        except:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return
        # If we were able to get a command line, run the job
        if command_line:
            try:
                log.debug( 'executing: %s' % command_line )
                proc = subprocess.Popen( args = command_line, 
                                         shell = True, 
                                         cwd = job_wrapper.working_directory, 
                                         stdout = subprocess.PIPE, 
                                         stderr = subprocess.PIPE,
                                         preexec_fn = os.setpgrp )
                job_wrapper.set_runner( 'local:///', proc.pid )
                stdout = proc.stdout.read() 
                stderr = proc.stderr.read()
                proc.wait()
                log.debug('execution finished: %s' % command_line)
            except Exception, exc:
                job_wrapper.fail( "failure running job", exception=True )
                log.exception("failure running job %d" % job_wrapper.job_id)
                return
        # Finish the job                
        job_wrapper.finish( stdout, stderr )

    def put( self, job_wrapper ):
        """Add a job to the queue (by job identifier)"""
        self.queue.put( job_wrapper )
    
    def shutdown( self ):
        """Attempts to gracefully shut down the worker threads"""
        log.info( "sending stop signal to worker threads" )
        for i in range( len( self.threads ) ):
            self.queue.put( self.STOP_SIGNAL )
        log.info( "local job runner stopped" )

def check_pid( pid ):
    try:
        os.kill( pid, 0 )
        return True
    except OSError, e:
        if e.errno == errno.ESRCH:
            log.debug( "local.check_pid(): PID %d is dead" % pid )
        else:
            log.warning( "local.check_pid(): Got errno %s when attempting to check PID %d: %s" %( errno.errorcode[e.errno], pid, e.strerror ) )
        return False

def stop_job( job ):
    pid = int( job.job_runner_external_id )
    if not check_pid( pid ):
        log.warning( "local.stop_job(): %s: PID %d was already dead or can't be signaled" %job.id )
        return
    for sig in [ 15, 9 ]:
        try:
            os.killpg( pid, sig )
        except OSError, e:
            log.warning( "local.stop_job(): %s: Got errno %s when attempting to signal %d to PID %d: %s" % ( job.id, errno.errorcode[e.errno], sig, pid, e.strerror ) )
            return  # give up
        sleep( 2 )
        if not check_pid( pid ):
            log.debug( "local.stop_job(): %s: PID %d successfully killed with signal %d" %( job.id, pid, sig ) )
            return
    else:
        log.warning( "local.stop_job(): %s: PID %d refuses to die after signaling TERM/KILL" %( job.id, pid ) )

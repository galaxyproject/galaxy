import logging
import subprocess
from Queue import Queue
import threading

from galaxy import model

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
            job_wrapper.change_state( 'running' )
            command_line = job_wrapper.get_command_line()
            if command_line:
                try:
                    log.debug( 'executing: %s' % command_line )
                    proc = subprocess.Popen( args = command_line, 
                                             shell = True, 
                                             stdout = subprocess.PIPE, 
                                             stderr = subprocess.PIPE )
                    stdout = proc.stdout.read() 
                    stderr = proc.stderr.read()
                    proc.stdout.close() 
                    proc.stderr.close()
                    log.debug('execution finished: %s' % command_line)
                except Exception, e:
                    job_wrapper.fail( "failure running job" )
                    log.exception( "failure running job id: %d" % job_wrapper.job_id  )
            else:
                stderr = stdout = ''
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
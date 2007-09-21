import logging,os
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
            stderr = stdout = command_line = ''
            # Prepare the job to run
            try:
                job_wrapper.prepare()
                command_line = job_wrapper.get_command_line()
            except:
                job_wrapper.fail( "failure preparing job", exception=True )
                log.exception( "failure running job id: %d" % job_wrapper.job_id  )
                continue
            # If we were able to get a command line, run the job
            if command_line:
                # patched by ross lazarus to really move to job_wrapper.working_directory for execution
                # required patches to use abspath for command line and for all datasets
                job_working_dir = job_wrapper.working_directory
                if not os.path.isabs(job_working_dir):
                     job_working_dir = os.path.abspath(job_working_dir)
                cl = command_line.split()
                if len(cl) >= 2: # assume we have a command?
                    for n,clp in enumerate(cl): # check for relative path in each cl parameter 
                        if (n > 0) and os.access(clp, os.R_OK)  : 
                              # ? is a path we might need to make absolute
                              cl[n] = os.path.abspath(clp) # convert to absolute path
                # this is dumb and there will be nasty edge cases but I'm not sure what else to do
                command_line = ' '.join(cl) # munged to absolute paths
                try:
                    log.debug( '## local.py job runner executing: %s in cwd = %s' %  (command_line,job_working_dir ))
                    proc = subprocess.Popen( args = command_line, 
                                             shell = True, 
                                             cwd = job_working_dir,
                                             stdout = subprocess.PIPE, 
                                             stderr = subprocess.PIPE )
                    stdout = proc.stdout.read() 
                    stderr = proc.stderr.read()
                    proc.stdout.close() 
                    proc.stderr.close()
                    log.debug('execution finished: %s' % command_line)
                except Exception, e:
                    job_wrapper.fail( "failure running job", exception=True )
                    log.exception( "failure running job id: %d, command_line=%s" % (job_wrapper.job_id,command_line)  )
                    continue
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

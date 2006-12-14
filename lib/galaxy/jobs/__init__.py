import logging, threading, sys, os, time, subprocess, string, tempfile, re

from galaxy import util, model
from galaxy.model import mapping

import pkg_resources
pkg_resources.require( "PasteDeploy" )

from paste.deploy.converters import asbool

from Queue import Queue

log = logging.getLogger( __name__ )

# States for running a job. These are NOT the same as data states
JOB_WAIT, JOB_ERROR, JOB_OK, JOB_READY = 'wait', 'error', 'ok', 'ready'

class JobQueue( object ):
    """
    Job queue backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Start the job queue with 'nworkers' worker threads"""
        self.app = app
        self.queue = Queue()
        self.dispatcher = DefaultJobDispatcher( app )
        self.monitor_thread = threading.Thread( target=self.run_next )
        self.monitor_thread.start()
        log.debug( "job manager started" )

    def run_next( self ):
        """Run the next job, waiting until one is available if neccesary"""
        while 1:
            job = self.queue.get()
            if job is self.STOP_SIGNAL:
                break
            try:
                # Run the job, requeue if not complete                    
                job_state = job.check_if_ready_to_run()
                if job_state == JOB_WAIT: 
                    self.put( job )
                    #log.debug( "the job has been requeued" )
                elif job_state == JOB_ERROR:
                    log.info( "job ended with an error" )
                elif job_state == JOB_READY:
                    self.dispatcher.put( job )
                else:
                    raise Exception( "Unknown Job State" )
            except:
                job.fail("failure running job")
                log.exception( "failure running job id: %d" % job.job_id  )
            
    def put( self, job_id, tool ):
        """Add a job to the queue (by job identifier)"""
        self.queue.put( JobWrapper( job_id, tool, self ) )
    
    def shutdown( self ):
        """Attempts to gracefully shut down the worker threads"""
        log.info( "sending stop signal to worker threads" )
        self.queue.put( self.STOP_SIGNAL )
        log.info( "job queue stopped" )
        self.dispatcher.shutdown()

class JobWrapper( object ):
    """
    A galaxy job -- an external process that will update one or more 'data'
    """
    def __init__(self, job_id, tool, queue ):
        self.job_id = job_id
        self.tool = tool
        self.queue = queue
        self.app = queue.app
        
    def fail( self, message ):
        """
        Indicate job failure by setting state and message on all output 
        datasets.
        """
        job = model.Job.get( self.job_id )
        job.refresh()
        for dataset_assoc in job.output_datasets:
            dataset = dataset_assoc.dataset
            dataset.refresh()
            dataset.state = dataset.states.ERROR
            dataset.blurb = 'tool error'
            dataset.info = "ERROR: " + message
            dataset.flush()
        job.state = model.Job.states.ERROR
        job.flush()
        
    def change_state( self, state ):
        job = model.Job.get( self.job_id )
        job.refresh()
        for dataset_assoc in job.output_datasets:
            dataset = dataset_assoc.dataset
            dataset.refresh()
            dataset.state = state
            dataset.flush()
        job.state = state
        job.flush()
        
    def check_if_ready_to_run( self ):
        job = model.Job.get( self.job_id )
        job.refresh()
        for dataset_assoc in job.input_datasets:
            idata = dataset_assoc.dataset
            idata.refresh()
            # an error in the input data causes us to bail immediately
            if idata.state == idata.states.ERROR:
                self.fail( "error in input data %d" % idata.hid )
                return JOB_ERROR
            elif idata.state == idata.states.FAKE:
                continue
            elif idata.state != idata.states.OK:
                # need to requeue
                return JOB_WAIT
        return JOB_READY
        
    def finish( self, stdout, stderr ):
        # default post job setup
        mapping.context.current.clear()
        job = model.Job.get( self.job_id )
        job.state = 'ok'
        for dataset_assoc in job.output_datasets:
            dataset = dataset_assoc.dataset
            dataset.refresh()
            dataset.state = model.Dataset.states.OK
            dataset.blurb = 'done'
            dataset.peek  = 'no peek'
            dataset.info  = stdout + stderr
            if dataset.has_data():
                dataset.set_peek()
            else:
                if stderr: 
                    dataset.state = model.Dataset.states.ERROR
                    dataset.blurb = "error"
                    job.state = "error"
                else:
                    dataset.blurb = "empty"
        # custom post process setup
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        self.tool.call_hook( 'exec_after_process', self.queue.app, inp_data=inp_data, 
                             out_data=out_data, param_dict=param_dict, 
                             tool=self.tool, stdout=stdout, stderr=stderr )
        # remove temporary file
        if job.param_filename: 
            os.remove( job.param_filename )
        # remove 'fake' datasets 
        for dataset_assoc in job.input_datasets:
            data = dataset_assoc.dataset
            if data.state == data.states.FAKE:
                data.delete()
        mapping.context.current.flush()
        log.debug('job ended, id: %d' % self.job_id )
        
    def get_command_line( self ):
        job = model.Job.get( self.job_id )
        return job.command_line
        
class DefaultJobDispatcher( object ):
    def __init__( self, app ):
        self.app = app
        self.use_pbs = asbool( app.config.use_pbs )
        import runners.local
        self.local_job_runner = runners.local.LocalJobRunner( app )
        if self.use_pbs:
            import runners.pbs
            self.pbs_job_runner = runners.pbs.PBSJobRunner( app )
            self.put = self.dispatch_pbs
        else:
            self.put = self.dispatch_default
            
    def dispatch_default( self, job_wrapper ):
        self.local_job_runner.put( job_wrapper )
            
    def dispatch_pbs( self, job_wrapper ):
        if "/tools/data_source" not in job_wrapper.get_command_line():
            self.local_job_runner.put( job_wrapper )
        else:
            self.pbs_job_runner.put( job_wrapper )
        
    def shutdown( self ):
        self.local_job_runner.shutdown()
        if self.use_pbs:
            self.pbs_job_runner.shutdown()  
    
    
import logging, threading, sys, os, time, subprocess, string, tempfile, re, traceback

from galaxy import util, model
from galaxy.model import mapping
from galaxy.datatypes.tabular import *
from galaxy.datatypes.interval import *

import pkg_resources
pkg_resources.require( "PasteDeploy" )

from paste.deploy.converters import asbool

from Queue import Queue, Empty

log = logging.getLogger( __name__ )

# States for running a job. These are NOT the same as data states
JOB_WAIT, JOB_ERROR, JOB_OK, JOB_READY = 'wait', 'error', 'ok', 'ready'

class Sleeper( object ):
    """
    Provides a 'sleep' method that sleeps for a number of seconds *unless*
    the notify method is called (from a different thread).
    """
    def __init__( self ):
        self.condition = threading.Condition()
    def sleep( self, seconds ):
        self.condition.acquire()
        self.condition.wait( seconds )
        self.condition.release()
    def wake( self ):
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()

class JobQueue( object ):
    """
    Job manager, waits for jobs to be runnable and then dispatches to 
    a JobRunner.
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Start the job manager"""
        self.app = app
        # Should we use IPC to communicate (needed if forking)
        self.track_jobs_in_database = app.config.get( 'track_jobs_in_database', False )
        
        # Check if any special scheduling policy should be used. If not, default is FIFO.
        sched_policy = app.config.get('job_scheduler_policy', 'FIFO')
        # Parse the scheduler policy string. The policy class implements a special queue. 
        # Ready-to-run jobs are inserted into this queue
        if sched_policy != 'FIFO' :
            try :
                self.use_policy = True
                if ":" in sched_policy :
                    modname , policy_class = sched_policy.split(":")
                    modfields = modname.split(".")
                    module = __import__(modname)
                    for mod in modfields[1:] : module = getattr( module, mod)
                    # instantiate the policy class
                    self.squeue = getattr( module , policy_class )(self.app)
                else :
                    self.use_policy = False
                    log.info("Scheduler policy not defined as expected, defaulting to FIFO")
            except AttributeError, detail : # try may throw AttributeError
                self.use_policy = False
                log.exception("Error while loading scheduler policy class, defaulting to FIFO")
        else :
            self.use_policy = False

        log.info("job scheduler policy is %s" %sched_policy)
        # Keep track of the pid that started the job manager, only it
        # has valid threads
        self.parent_pid = os.getpid()
        # Contains new jobs. Note this is not used if track_jobs_in_database is True
        self.queue = Queue()
        
        # Contains jobs that are waiting (only use from monitor thread)
        ## This and new_jobs[] are closest to a "Job Queue"
        self.waiting = []
                
        # Helper for interruptable sleep
        self.sleeper = Sleeper()
        self.running = True
        self.dispatcher = DefaultJobDispatcher( app )
        self.monitor_thread = threading.Thread( target=self.monitor )
        self.monitor_thread.start()        
        log.info( "job manager started" )

    def monitor( self ):
        """
        Continually iterate the waiting jobs, checking is each is ready to 
        run and dispatching if so.
        """
        # HACK: Delay until after forking, we need a way to do post fork notification!!!
        time.sleep( 10 )
        while self.running:
            try:
                self.monitor_step()
            except:
                log.exception( "Exception in monitor_step" )
            # Sleep
            self.sleeper.sleep( 1 )
            
    def monitor_step( self ):
        """
        Called repeatedly by `monitor` to process waiting jobs. Gets any new
        jobs (either from the database or from its own queue), then iterates
        over all new and waiting jobs to check the state of the jobs each
        depends on. If the job has dependencies that have not finished, it
        it goes to the waiting queue. If the job has dependencies with errors,
        it is marked as having errors and removed from the queue. Otherwise,
        the job is dispatched.
        """
        # Pull all new jobs from the queue at once
        new_jobs = []
        if self.track_jobs_in_database:
            model = self.app.model
            for j in model.Job.select( model.Job.c.state == 'new' ):
                job = JobWrapper( j.id, self.app.toolbox.tools_by_id[ j.tool_id ], self )
                new_jobs.append( job )
        else:
            try:
                while 1:
                    message = self.queue.get_nowait()
                    if message is self.STOP_SIGNAL:
                        return
                    # Unpack the message
                    job_id, tool_id = message
                    # Create a job wrapper from it
                    job = JobWrapper( job_id, self.app.toolbox.tools_by_id[ tool_id ], self )
                    # Append to watch queue
                    new_jobs.append( job )
            except Empty:
                pass  
        # Iterate over new and waiting jobs and look for any that are 
        # ready to run
        new_waiting = []
        for job in ( new_jobs + self.waiting ):
            try:
                # Check the job's dependencies, requeue if they're not done                    
                job_state = job.check_if_ready_to_run()
                if job_state == JOB_WAIT: 
                    new_waiting.append( job )
                elif job_state == JOB_ERROR:
                    log.info( "job %d ended with an error" % job.job_id )
                elif job_state == JOB_READY:
                    # If special queuing is enabled, put the ready jobs in the special queue
                    if self.use_policy :
                        self.squeue.put( job ) 
                        log.debug( "job %d put in policy queue" % job.job_id )
                    else : # or dispatch the job directly
                        self.dispatcher.put( job )
                        log.debug( "job %d dispatched" % job.job_id)
                else:
                    log.error( "unknown job state '%s' for job %d" % ( job_state, job.job_id ))
            except:
                log.exception( "failure running job %d" % job.job_id )
        # Update the waiting list
        self.waiting = new_waiting
        # If special (e.g. fair) scheduling is enabled, dispatch all jobs
        # currently in the special queue    
        if self.use_policy :
            while 1:
                try:
                    sjob = self.squeue.get()
                    self.dispatcher.put( sjob )
                    log.debug( "job %d dispatched" % sjob.job_id )
                except Empty: 
                    # squeue is empty, so stop dispatching
                    break
                except: # if something else breaks while dispatching
                    job.fail( "failure dispatching job" )
                    log.exception( "failure running job %d" % sjob.job_id )
            
    def put( self, job_id, tool ):
        """Add a job to the queue (by job identifier)"""
        if not self.track_jobs_in_database:
            self.queue.put( ( job_id, tool.id ) )
            self.sleeper.wake()
    
    def shutdown( self ):
        """Attempts to gracefully shut down the worker thread"""
        if self.parent_pid != os.getpid():
            # We're not the real job queue, do nothing
            return
        else:
            log.info( "sending stop signal to worker thread" )
            self.running = False
            if not self.track_jobs_in_database:
                self.queue.put( self.STOP_SIGNAL )
            self.sleeper.wake()
            log.info( "job queue stopped" )
            self.dispatcher.shutdown()
            

class JobWrapper( object ):
    """
    Wraps a 'model.Job' with convience methods for running processes and 
    state management.
    """
    def __init__(self, job_id, tool, queue ):
        self.job_id = job_id
        self.tool = tool
        self.queue = queue
        self.app = queue.app
        self.extra_filenames = []
        self.working_directory = None
        self.command_line = None
        
    def get_param_dict( self ):
        """
        Restore the dictionary of parameters from the database.
        """
        job = model.Job.get( self.job_id )
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        return param_dict
        
    def prepare( self ):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        # Create the working directory
        self.working_directory = \
            os.path.join( self.app.config.job_working_directory, str( self.job_id ) )
        if not os.path.exists( self.working_directory ):
            os.mkdir( self.working_directory )
        # Restore parameters from the database
        job = model.Job.get( self.job_id )
        incoming = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        incoming = self.tool.params_from_strings( incoming, self.app )
        # Resore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        # add some useful session info to param_dict via incoming - ross august 2007
        # these can be passed on the commandline if wanted as $userId $userEmail
        if job.history.user: # check for anonymous user!
             userId = '%d' % job.history.user.id
             userEmail = str(job.history.user.email)
        else:
             userId = 'Anonymous'
             userEmail = 'Anonymous'
        incoming['userId'] = userId
        incoming['userEmail'] = userEmail
        # Build params, done before hook so hook can use
        param_dict = self.tool.build_param_dict( incoming, inp_data, out_data )
        # Run the before queue ("exec_before_job") hook "trans" is no
        # longer available to this hook, and has been replaced with
        # app - 5/31/2007, by INS
        # job added so we can get at the user if needed 14/august/2007 ross
        self.tool.call_hook( 'exec_before_job', self.queue.app, inp_data=inp_data, 
                             out_data=out_data, tool=self.tool, param_dict=incoming)
        mapping.context.current.flush()
        # Build any required config files
        config_filenames = self.tool.build_config_files( param_dict, self.working_directory )
        # FIXME: Build the param file (might return None, DEPRECATED)
        param_filename = self.tool.build_param_file( param_dict, self.working_directory )
        # Build the job's command line
        self.command_line = self.tool.build_command_line( param_dict )
        # Return list of all extra files
        extra_filenames = config_filenames
        if param_filename is not None:
            extra_filenames.append( param_filename )
        self.param_dict = param_dict
        self.extra_filenames = extra_filenames
        return extra_filenames
        
    def fail( self, message, exception=False ):
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
            dataset.info = message
            dataset.set_size()
            dataset.flush()
        job.state = model.Job.states.ERROR
        job.command_line = self.command_line
        # If the failure is due to a Galaxy framework exception, save 
        # the traceback
        if exception:
            job.traceback = traceback.format_exc()
        job.flush()
        self.cleanup()
        
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
        """
        Check if a job is ready to run by verifying that each of its input 
        datasets is ready (specifically in the OK state). If any input dataset
        has an error, fail the job and return JOB_ERROR. If all input datasets
        are in OK state, return JOB_READY indicating that the job can be 
        dispatched. Otherwise, return JOB_WAIT indicating that input datasets
        are still being prepared.
        """
        job = model.Job.get( self.job_id )
        job.refresh()
        for dataset_assoc in job.input_datasets:
            idata = dataset_assoc.dataset
            idata.refresh()
            # an error in the input data causes us to bail immediately
            if idata.state == idata.states.ERROR:
                self.fail( "error in input data %d" % idata.hid )
                return JOB_ERROR
            elif idata.state != idata.states.OK:
                # need to requeue
                return JOB_WAIT
        return JOB_READY
        
    def finish( self, stdout, stderr ):
        """
        Called to indicate that the associated command has been run. Updates 
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files. 
        """
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
            dataset.set_size()
            if dataset.has_data():
                # Only set metadata values if they are missing...
                if dataset.missing_meta():
                    dataset.set_meta()
                else:
                    # ...however, some tools add / remove columns,
                    # so we have to reset the readonly metadata values
                    dataset.set_readonly_meta()
                dataset.set_peek()
            else:
                dataset.blurb = "empty"
            if stderr: 
                dataset.state = model.Dataset.states.ERROR
                dataset.blurb = "error"
                job.state = "error"
        # Save stdout and stderr    
        if len( stdout ) > 32768:
            log.error( "stdout for job %d is greater than 32K, only first part will be logged to database" % job.id )
        job.stdout = stdout[:32768]
        if len( stderr ) > 32768:
            log.error( "stderr for job %d is greater than 32K, only first part will be logged to database" % job.id )
        job.stderr = stderr[:32768]  
        # custom post process setup
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] ) # why not re-use self.param_dict here?
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        # Check for and move associated_files
        self.tool.collect_associated_files(out_data)
        # Create generated output children and primary datasets and add to param_dict
        collected_datasets = {'children':self.tool.collect_child_datasets(out_data),'primary':self.tool.collect_primary_datasets(out_data)}
        param_dict.update({'__collected_datasets__':collected_datasets})
        # Call 'exec_after_process' hook
        self.tool.call_hook( 'exec_after_process', self.queue.app, inp_data=inp_data, 
                             out_data=out_data, param_dict=param_dict, 
                             tool=self.tool, stdout=stdout, stderr=stderr )
        # hack by ross for testing passing self.param_dict rather than recreating it
        self.param_dict.update({'__collected_datasets__':collected_datasets})
        self.tool.call_hook( 'exec_after_process_plus', self.queue.app, inp_data=inp_data, 
                             out_data=out_data, param_dict=self.param_dict, 
                             tool=self.tool, stdout=stdout, stderr=stderr )
        # TODO
        # validate output datasets
        job.command_line = self.command_line
        mapping.context.current.flush()
        log.debug( 'job %d ended' % self.job_id )
        self.cleanup()
        
    def cleanup( self ):
        # remove temporary files
        for fname in self.extra_filenames: 
            os.remove( fname )
        if self.working_directory is not None:
            os.rmdir( self.working_directory ) 
        
    def get_command_line( self ):
        return self.command_line
    
    def get_session_id( self ):
        job = model.Job.get( self.job_id )
        return job.session_id

    def get_input_fnames( self ):
        job = model.Job.get( self.job_id )
        return [ da.dataset.file_name for da in job.input_datasets ]

    def get_output_fnames( self ):
        job = model.Job.get( self.job_id )
        return [ da.dataset.file_name for da in job.output_datasets ]

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
        log.debug( "dispatch_default(): dispatching job %d to local runner" %job_wrapper.job_id )
            
    def dispatch_pbs( self, job_wrapper ):
        # command_line = job_wrapper.get_command_line()
        # HACK: Need a more robust way for tools to assert whether they should
        #       be run on the cluster.
        command_line = job_wrapper.tool.command
        if ( not command_line ) or ( "/tools/data_source" in command_line ):
            log.debug( "dispatching job %d to local runner" %job_wrapper.job_id )
            self.local_job_runner.put( job_wrapper )
        else:
            self.pbs_job_runner.put( job_wrapper )
            log.debug( "dispatch_pbs(): dispatching job %d to pbs runner" %job_wrapper.job_id )
        
    def shutdown( self ):
        self.local_job_runner.shutdown()
        if self.use_pbs:
            self.pbs_job_runner.shutdown()  
    

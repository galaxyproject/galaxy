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
JOB_WAIT, JOB_ERROR, JOB_OK, JOB_READY, JOB_DELETED = 'wait', 'error', 'ok', 'ready', 'deleted'

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
    def __init__( self, app, dispatcher ):
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
        self.dispatcher = dispatcher
        self.monitor_thread = threading.Thread( target=self.monitor )
        self.monitor_thread.start()        
        log.info( "job manager started" )
        self.check_jobs_at_startup()

    def check_jobs_at_startup( self ):
        """
        Checks all jobs that are in the 'running' or 'queued' state in the
        database and requeues or cleans up as necessary.  Only run as the
        job manager starts.
        """
        model = self.app.model
        # Jobs in the NEW state won't be requeued unless we're tracking in the database
        if not self.track_jobs_in_database:
            for job in model.Job.select( model.Job.c.state == model.Job.states.NEW ):
                log.debug( "no runner: %s is still in new state, adding to the jobs queue" %job.id )
                self.queue.put( ( job.id, job.tool_id ) )
        for job in model.Job.select( (model.Job.c.state == model.Job.states.RUNNING)
                                 | (model.Job.c.state == model.Job.states.QUEUED) ):
            if job.job_runner_name is not None:
                # why are we passing the queue to the wrapper?
                job_wrapper = JobWrapper( job.id, self.app.toolbox.tools_by_id[ job.tool_id ], self )
                self.dispatcher.recover( job, job_wrapper )

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
            for j in model.Job.select( model.Job.c.state == model.Job.states.NEW ):
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
                    if not self.track_jobs_in_database:
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
                elif job_state == JOB_DELETED:
                    log.debug( "job %d deleted by user while still queued" % job.job_id )
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
        self.galaxy_lib_dir = None
        
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
        # Do any validation that could not be done at job creation
        self.tool.handle_unvalidated_param_values( incoming, self.app )
        # Restore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        # These can be passed on the command line if wanted as $userId $userEmail
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
        # Run the before queue ("exec_before_job") hook
        self.tool.call_hook( 'exec_before_job', self.queue.app, inp_data=inp_data, 
                             out_data=out_data, tool=self.tool, param_dict=incoming)
        mapping.context.current.flush()
        # Build any required config files
        config_filenames = self.tool.build_config_files( param_dict, self.working_directory )
        # FIXME: Build the param file (might return None, DEPRECATED)
        param_filename = self.tool.build_param_file( param_dict, self.working_directory )
        # Build the job's command line
        self.command_line = self.tool.build_command_line( param_dict )
        # FIXME: for now, tools get Galaxy's lib dir in their path
        if self.command_line and self.command_line.startswith( 'python' ):
            self.galaxy_lib_dir = os.path.abspath( "lib" ) # cwd = galaxy root
        # We need command_line persisted to the db in order for Galaxy to re-queue the job
        # if the server was stopped and restarted before the job finished
        job.command_line = self.command_line
        job.flush()
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
        # if the job was deleted, don't fail it
        if job.state == job.states.DELETED:
            self.cleanup()
            return
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
        
    def change_state( self, state, info = False ):
        job = model.Job.get( self.job_id )
        job.refresh()
        for dataset_assoc in job.output_datasets:
            dataset = dataset_assoc.dataset
            dataset.refresh()
            dataset.state = state
            if info:
                dataset.info = info
            dataset.flush()
        if info:
            job.info = info
        job.state = state
        job.flush()

    def get_state( self ):
        job = model.Job.get( self.job_id )
        job.refresh()
        return job.state

    def set_runner( self, runner_url, external_id ):
        job = model.Job.get( self.job_id )
        job.refresh()
        job.job_runner_name = runner_url
        job.job_runner_external_id = external_id
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
            if not idata: continue
            idata.refresh()
            idata.dataset.refresh() #we need to refresh the base Dataset, since that is where 'state' is stored
            # don't run jobs for which the input dataset was deleted
            if idata.deleted == True:
                self.fail( "input data %d was deleted before this job ran" % idata.hid )
                return JOB_ERROR
            # an error in the input data causes us to bail immediately
            elif idata.state == idata.states.ERROR:
                self.fail( "error in input data %d" % idata.hid )
                return JOB_ERROR
            elif idata.state != idata.states.OK:
                # need to requeue
                return JOB_WAIT
        if job.state == model.Job.states.DELETED:
            return JOB_DELETED
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
        # TODO: change PBS to use fail() instead of finish()
        # if the job was deleted, don't finish it
        if job.state == job.states.DELETED:
            self.cleanup()
            return
        if stderr:
            job.state = "error"
        else:
            job.state = 'ok'
        for dataset_assoc in job.output_datasets:
            for dataset in dataset_assoc.dataset.dataset.history_associations: #need to update all associated output hdas, i.e. history was shared with job running
                dataset.blurb = 'done'
                dataset.peek  = 'no peek'
                dataset.info  = stdout + stderr
                dataset.set_size()
                if stderr:
                    dataset.blurb = "error"
                elif dataset.has_data():
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
                dataset.flush()
            if stderr: 
                dataset_assoc.dataset.dataset.state = model.Dataset.states.ERROR
            else:
                dataset_assoc.dataset.dataset.state = model.Dataset.states.OK
            dataset_assoc.dataset.dataset.flush()
        
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
        # TODO
        # validate output datasets
        job.command_line = self.command_line
        mapping.context.current.flush()
        log.debug( 'job %d ended' % self.job_id )
        self.cleanup()
        
    def cleanup( self ):
        # remove temporary files
        try:
            for fname in self.extra_filenames: 
                os.remove( fname )
            if self.working_directory is not None:
                os.rmdir( self.working_directory ) 
        except:
            log.exception( "Unable to cleanup job %s" % self.job_id )
        
    def get_command_line( self ):
        return self.command_line
    
    def get_session_id( self ):
        job = model.Job.get( self.job_id )
        return job.session_id

    def get_input_fnames( self ):
        job = model.Job.get( self.job_id )
        return [ da.dataset.file_name for da in job.input_datasets if da.dataset ]

    def get_output_fnames( self ):
        job = model.Job.get( self.job_id )
        return [ da.dataset.file_name for da in job.output_datasets ]

class DefaultJobDispatcher( object ):
    def __init__( self, app ):
        self.app = app
        self.job_runners = {}
        start_job_runners = ["local"]
        if app.config.start_job_runners is not None:
            start_job_runners.extend( app.config.start_job_runners.split(",") )
        for runner_name in start_job_runners:
            if runner_name == "local":
                import runners.local
                self.job_runners[runner_name] = runners.local.LocalJobRunner( app )
            elif runner_name == "pbs":
                import runners.pbs
                self.job_runners[runner_name] = runners.pbs.PBSJobRunner( app )
            elif runner_name == "sge":
                import runners.sge
                self.job_runners[runner_name] = runners.sge.SGEJobRunner( app )
            else:
                log.error( "Unable to start unknown job runner: %s" %runner_name )
            
    def put( self, job_wrapper ):
        runner_name = ( job_wrapper.tool.job_runner.split(":", 1) )[0]
        log.debug( "dispatching job %d to %s runner" %( job_wrapper.job_id, runner_name ) )
        self.job_runners[runner_name].put( job_wrapper )

    def stop( self, job ):
        runner_name = ( job.job_runner_name.split(":", 1) )[0]
        log.debug( "stopping job %d in %s runner" %( job.id, runner_name ) )
        self.job_runners[runner_name].stop_job( job )

    def recover( self, job, job_wrapper ):
        runner_name = ( job.job_runner_name.split(":", 1) )[0]
        log.debug( "recovering job %d in %s runner" %( job.id, runner_name ) )
        self.job_runners[runner_name].recover( job, job_wrapper )

    def shutdown( self ):
        for runner in self.job_runners.itervalues():
            runner.shutdown()

class JobStopQueue( object ):
    """
    A queue for jobs which need to be terminated prematurely.
    """
    STOP_SIGNAL = object()
    def __init__( self, app, dispatcher ):
        self.app = app
        self.dispatcher = dispatcher

        # Keep track of the pid that started the job manager, only it
        # has valid threads
        self.parent_pid = os.getpid()
        # Contains new jobs. Note this is not used if track_jobs_in_database is True
        self.queue = Queue()

        # Contains jobs that are waiting (only use from monitor thread)
        self.waiting = []

        # Helper for interruptable sleep
        self.sleeper = Sleeper()
        self.running = True
        self.monitor_thread = threading.Thread( target=self.monitor )
        self.monitor_thread.start()        
        log.info( "job stopper started" )

    def monitor( self ):
        """
        Continually iterate the waiting jobs, stop any that are found.
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
        Called repeatedly by `monitor` to stop jobs.
        """
        # Pull all new jobs from the queue at once
        jobs = []
        try:
            while 1:
                job = self.queue.get_nowait()
                if job is self.STOP_SIGNAL:
                    return
                # Append to watch queue
                jobs.append( job )
        except Empty:
            pass  

        for job in jobs:
            # jobs in a non queued/running/new state do not need to be stopped
            if job.state not in [ model.Job.states.QUEUED, model.Job.states.RUNNING, model.Job.states.NEW ]:
                return
            # job has multiple datasets that aren't parent/child and not all of them are deleted.
            if not self.check_if_output_datasets_deleted( job.id ):
                return
            self.mark_deleted( job.id )
            # job is in JobQueue or FooJobRunner, will be dequeued due to state change above
            if job.job_runner_name is None:
                return
            # tell the dispatcher to stop the job
            self.dispatcher.stop( job )

    def check_if_output_datasets_deleted( self, job_id ):
        job = model.Job.get( job_id )
        for dataset_assoc in job.output_datasets:
            dataset = dataset_assoc.dataset
            dataset.refresh()
            #only the originator of the job can delete a dataset to cause
            #cancellation of the job, no need to loop through history_associations
            if not dataset.deleted:
                return False
        return True

    def mark_deleted( self, job_id ):
        job = model.Job.get( job_id )
        job.refresh()
        job.state = job.states.DELETED
        job.info = "Job deleted by user before it completed."
        job.flush()
        for dataset_assoc in job.output_datasets:
            dataset = dataset_assoc.dataset
            dataset.refresh()
            dataset.deleted = True
            dataset.state = dataset.states.DISCARDED
            dataset.dataset.flush()
            for dataset in dataset.dataset.history_associations:
                #propagate info across shared datasets
                dataset.deleted = True
                dataset.blurb = 'deleted'
                dataset.peek = 'Job deleted'
                dataset.info = 'Job deleted by user before it completed'
                dataset.flush()

    def put( self, job ):
        self.queue.put( job )

    def shutdown( self ):
        """Attempts to gracefully shut down the worker thread"""
        if self.parent_pid != os.getpid():
            # We're not the real job queue, do nothing
            return
        else:
            log.info( "sending stop signal to worker thread" )
            self.running = False
            self.queue.put( self.STOP_SIGNAL )
            self.sleeper.wake()
            log.info( "job stopper stopped" )

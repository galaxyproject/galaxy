import logging, threading, sys, os, time, subprocess, string, tempfile, re, traceback, shutil

from galaxy import util, model
from galaxy.model.orm import lazyload
from galaxy.datatypes.tabular import *
from galaxy.datatypes.interval import *
from galaxy.datatypes import metadata
from galaxy.util.json import from_json_string
from galaxy.util.expressions import ExpressionContext
from galaxy.jobs.actions.post import ActionBox

import pkg_resources
pkg_resources.require( "PasteDeploy" )

from paste.deploy.converters import asbool

from Queue import Queue, Empty

log = logging.getLogger( __name__ )

# States for running a job. These are NOT the same as data states
JOB_WAIT, JOB_ERROR, JOB_INPUT_ERROR, JOB_INPUT_DELETED, JOB_READY, JOB_DELETED, JOB_ADMIN_DELETED = 'wait', 'error', 'input_error', 'input_deleted', 'ready', 'deleted', 'admin_deleted'

# This file, if created in the job's working directory, will be used for
# setting advanced metadata properties on the job and its associated outputs.
# This interface is currently experimental, is only used by the upload tool,
# and should eventually become API'd
TOOL_PROVIDED_JOB_METADATA_FILE = 'galaxy.json'

class JobManager( object ):
    """
    Highest level interface to job management.
    
    TODO: Currently the app accesses "job_queue" and "job_stop_queue" directly.
          This should be decoupled. 
    """
    def __init__( self, app ):
        self.app = app
        if self.app.config.get_bool( "enable_job_running", True ):
            # The dispatcher launches the underlying job runners
            self.dispatcher = DefaultJobDispatcher( app )
            # Queues for starting and stopping jobs
            self.job_queue = JobQueue( app, self.dispatcher )
            self.job_stop_queue = JobStopQueue( app, self.dispatcher )
        else:
            self.job_queue = self.job_stop_queue = NoopQueue()
    def shutdown( self ):
        self.job_queue.shutdown()
        self.job_stop_queue.shutdown()

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
        self.sa_session = app.model.context
        self.job_lock = False
        # Should we read jobs form the database, or use an in memory queue
        self.track_jobs_in_database = app.config.get_bool( 'track_jobs_in_database', False )
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
        self.monitor_thread = threading.Thread( target=self.__monitor )
        self.monitor_thread.start()        
        log.info( "job manager started" )
        if app.config.get_bool( 'enable_job_recovery', True ):
            self.__check_jobs_at_startup()

    def __check_jobs_at_startup( self ):
        """
        Checks all jobs that are in the 'new', 'queued' or 'running' state in
        the database and requeues or cleans up as necessary.  Only run as the
        job manager starts.
        """
        model = self.app.model
        for job in self.sa_session.query( model.Job ).filter( model.Job.state == model.Job.states.NEW ):
            if job.tool_id not in self.app.toolbox.tools_by_id:
                log.warning( "Tool '%s' removed from tool config, unable to recover job: %s" % ( job.tool_id, job.id ) )
                JobWrapper( job, self ).fail( 'This tool was disabled before the job completed.  Please contact your Galaxy administrator, or' )
            else:
                log.debug( "no runner: %s is still in new state, adding to the jobs queue" %job.id )
                self.queue.put( ( job.id, job.tool_id ) )
        for job in self.sa_session.query( model.Job ).filter( ( model.Job.state == model.Job.states.RUNNING ) | ( model.Job.state == model.Job.states.QUEUED ) ):
            if job.tool_id not in self.app.toolbox.tools_by_id:
                log.warning( "Tool '%s' removed from tool config, unable to recover job: %s" % ( job.tool_id, job.id ) )
                JobWrapper( job, self ).fail( 'This tool was disabled before the job completed.  Please contact your Galaxy administrator, or' )
            elif job.job_runner_name is None:
                log.debug( "no runner: %s is still in queued state, adding to the jobs queue" %job.id )
                if self.track_jobs_in_database:
                    job.state = model.Job.states.NEW
                else:
                    self.queue.put( ( job.id, job.tool_id ) )
            else:
                job_wrapper = JobWrapper( job, self )
                self.dispatcher.recover( job, job_wrapper )
        if self.sa_session.dirty:
            self.sa_session.flush()

    def __monitor( self ):
        """
        Continually iterate the waiting jobs, checking is each is ready to 
        run and dispatching if so.
        """
        # HACK: Delay until after forking, we need a way to do post fork notification!!!
        time.sleep( 10 )
        while self.running:
            try:
                self.__monitor_step()
            except:
                log.exception( "Exception in monitor_step" )
            # Sleep
            self.sleeper.sleep( 1 )

    def __monitor_step( self ):
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
            # Clear the session so we get fresh states for job and all datasets
            self.sa_session.expunge_all()
            # Fetch all new jobs
            new_jobs = self.sa_session.query( model.Job ) \
                            .options( lazyload( "external_output_metadata" ), lazyload( "parameters" ) ) \
                            .filter( model.Job.state == model.Job.states.NEW ).all()
        else:
            try:
                while 1:
                    message = self.queue.get_nowait()
                    if message is self.STOP_SIGNAL:
                        return
                    # Unpack the message
                    job_id, tool_id = message
                    # Create a job wrapper from it
                    job = self.sa_session.query( model.Job ).get( job_id )
                    # Append to watch queue
                    new_jobs.append( job )
            except Empty:
                pass
        # Iterate over new and waiting jobs and look for any that are 
        # ready to run
        new_waiting = []
        for job in ( new_jobs + self.waiting ):
            try:
                # Since we don't expunge when not tracking jobs in the
                # database, refresh the job here so it's not stale.
                if not self.track_jobs_in_database:
                    self.sa_session.refresh( job )
                # Check the job's dependencies, requeue if they're not done                    
                job_state = self.__check_if_ready_to_run( job )
                if job_state == JOB_WAIT:
                    if not self.track_jobs_in_database:
                        new_waiting.append( job )
                elif job_state == JOB_INPUT_ERROR:
                    log.info( "job %d unable to run: one or more inputs in error state" % job.id )
                elif job_state == JOB_INPUT_DELETED:
                    log.info( "job %d unable to run: one or more inputs deleted" % job.id )
                elif job_state == JOB_READY:
                    if self.job_lock:
                        log.info( "Job dispatch attempted for %s, but prevented by administrative lock." % job.id )
                        if not self.track_jobs_in_database:
                            new_waiting.append( job )
                    else:
                        self.dispatcher.put( JobWrapper( job, self ) )
                        log.info( "job %d dispatched" % job.id )
                elif job_state == JOB_DELETED:
                    log.info( "job %d deleted by user while still queued" % job.id )
                elif job_state == JOB_ADMIN_DELETED:
                    job.info( "job %d deleted by admin while still queued" % job.id )
                else:
                    log.error( "unknown job state '%s' for job %d" % ( job_state, job.id ) )
                    if not self.track_jobs_in_database:
                        new_waiting.append( job )
            except Exception, e:
                log.exception( "failure running job %d" % job.id )
        # Update the waiting list
        self.waiting = new_waiting
        # Done with the session
        self.sa_session.remove()
        
    def __check_if_ready_to_run( self, job ):
        """
        Check if a job is ready to run by verifying that each of its input
        datasets is ready (specifically in the OK state). If any input dataset
        has an error, fail the job and return JOB_INPUT_ERROR. If any input
        dataset is deleted, fail the job and return JOB_INPUT_DELETED.  If all
        input datasets are in OK state, return JOB_READY indicating that the
        job can be dispatched. Otherwise, return JOB_WAIT indicating that input
        datasets are still being prepared.
        """
        if job.state == model.Job.states.DELETED:
            return JOB_DELETED
        elif job.state == model.Job.states.ERROR:
            return JOB_ADMIN_DELETED
        for dataset_assoc in job.input_datasets:
            idata = dataset_assoc.dataset
            if not idata:
                continue
            # don't run jobs for which the input dataset was deleted
            if idata.deleted:
                JobWrapper( job, self ).fail( "input data %d (file: %s) was deleted before the job started" % ( idata.hid, idata.file_name ) )
                return JOB_INPUT_DELETED
            # an error in the input data causes us to bail immediately
            elif idata.state == idata.states.ERROR:
                JobWrapper( job, self ).fail( "input data %d is in error state" % ( idata.hid ) )
                return JOB_INPUT_ERROR
            elif idata.state != idata.states.OK and not ( idata.state == idata.states.SETTING_METADATA and job.tool_id is not None and job.tool_id == self.app.datatypes_registry.set_external_metadata_tool.id ):
                # need to requeue
                return JOB_WAIT
        return JOB_READY
            
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
    def __init__( self, job, queue ):
        self.job_id = job.id
        self.session_id = job.session_id
        self.user_id = job.user_id
        self.tool = queue.app.toolbox.tools_by_id.get( job.tool_id, None )
        self.queue = queue
        self.app = queue.app
        self.sa_session = self.app.model.context
        self.extra_filenames = []
        self.command_line = None
        self.galaxy_lib_dir = None
        # With job outputs in the working directory, we need the working
        # directory to be set before prepare is run, or else premature deletion
        # and job recovery fail.
        self.working_directory = \
            os.path.join( self.app.config.job_working_directory, str( self.job_id ) )
        self.output_paths = None
        self.tool_provided_job_metadata = None
        self.external_output_metadata = metadata.JobExternalOutputMetadataWrapper( job ) #wrapper holding the info required to restore and clean up from files used for setting metadata externally
        
    def get_param_dict( self ):
        """
        Restore the dictionary of parameters from the database.
        """
        job = self.sa_session.query( model.Job ).get( self.job_id )
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        return param_dict
        
    def prepare( self ):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        self.sa_session.expunge_all() #this prevents the metadata reverting that has been seen in conjunction with the PBS job runner
        if not os.path.exists( self.working_directory ):
            os.mkdir( self.working_directory )
        # Restore parameters from the database
        job = self.sa_session.query( model.Job ).get( self.job_id )
        if job.user is None and job.galaxy_session is None:
            raise Exception( 'Job %s has no user and no session.' % job.id )
        incoming = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        incoming = self.tool.params_from_strings( incoming, self.app )
        # Do any validation that could not be done at job creation
        self.tool.handle_unvalidated_param_values( incoming, self.app )
        # Restore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )
        # These can be passed on the command line if wanted as $userId $userEmail
        if job.history and job.history.user: # check for anonymous user!
            userId = '%d' % job.history.user.id
            userEmail = str(job.history.user.email)
        else:
            userId = 'Anonymous'
            userEmail = 'Anonymous'
        incoming['userId'] = userId
        incoming['userEmail'] = userEmail
        # Build params, done before hook so hook can use
        param_dict = self.tool.build_param_dict( incoming, inp_data, out_data, self.get_output_fnames(), self.working_directory )
        # Certain tools require tasks to be completed prior to job execution
        # ( this used to be performed in the "exec_before_job" hook, but hooks are deprecated ).
        self.tool.exec_before_job( self.queue.app, inp_data, out_data, param_dict )
        # Run the before queue ("exec_before_job") hook
        self.tool.call_hook( 'exec_before_job', self.queue.app, inp_data=inp_data, 
                             out_data=out_data, tool=self.tool, param_dict=incoming)
        self.sa_session.flush()
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
        self.sa_session.add( job )
        self.sa_session.flush()
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
        job = self.sa_session.query( model.Job ).get( self.job_id )
        self.sa_session.refresh( job )
        # if the job was deleted, don't fail it
        if not job.state == model.Job.states.DELETED:
            # Check if the failure is due to an exception
            if exception:
                # Save the traceback immediately in case we generate another
                # below
                job.traceback = traceback.format_exc()
                # Get the exception and let the tool attempt to generate
                # a better message
                etype, evalue, tb =  sys.exc_info()
                m = self.tool.handle_job_failure_exception( evalue )
                if m:
                    message = m
            if self.app.config.outputs_to_working_directory:
                for dataset_path in self.get_output_fnames():
                    try:
                        shutil.move( dataset_path.false_path, dataset_path.real_path )
                        log.debug( "fail(): Moved %s to %s" % ( dataset_path.false_path, dataset_path.real_path ) )
                    except ( IOError, OSError ), e:
                        log.error( "fail(): Missing output file in working directory: %s" % e )
            for dataset_assoc in job.output_datasets + job.output_library_datasets:
                dataset = dataset_assoc.dataset
                self.sa_session.refresh( dataset )
                dataset.state = dataset.states.ERROR
                dataset.blurb = 'tool error'
                dataset.info = message
                dataset.set_size()
                if dataset.ext == 'auto':
                    dataset.extension = 'data'
                self.sa_session.add( dataset )
                self.sa_session.flush()
            job.state = model.Job.states.ERROR
            job.command_line = self.command_line
            job.info = message
            self.sa_session.add( job )
            self.sa_session.flush()
        # If the job was deleted, call tool specific fail actions (used for e.g. external metadata) and clean up
        if self.tool:
            self.tool.job_failed( self, message, exception )
        self.cleanup()
        
    def change_state( self, state, info = False ):
        job = self.sa_session.query( model.Job ).get( self.job_id )
        self.sa_session.refresh( job )
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            dataset = dataset_assoc.dataset
            self.sa_session.refresh( dataset )
            dataset.state = state
            if info:
                dataset.info = info
            self.sa_session.add( dataset )
            self.sa_session.flush()
        if info:
            job.info = info
        job.state = state
        self.sa_session.add( job )
        self.sa_session.flush()

    def get_state( self ):
        job = self.sa_session.query( model.Job ).get( self.job_id )
        self.sa_session.refresh( job )
        return job.state

    def set_runner( self, runner_url, external_id ):
        job = self.sa_session.query( model.Job ).get( self.job_id )
        self.sa_session.refresh( job )
        job.job_runner_name = runner_url
        job.job_runner_external_id = external_id
        self.sa_session.add( job )
        self.sa_session.flush()
        
    def finish( self, stdout, stderr ):
        """
        Called to indicate that the associated command has been run. Updates 
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files. 
        """
        # default post job setup
        self.sa_session.expunge_all()
        job = self.sa_session.query( model.Job ).get( self.job_id )
        # if the job was deleted, don't finish it
        if job.state == job.states.DELETED:
            self.cleanup()
            return
        elif job.state == job.states.ERROR:
            # Job was deleted by an administrator
            self.fail( job.info )
            return
        if stderr:
            job.state = "error"
        else:
            job.state = 'ok'
        if self.app.config.outputs_to_working_directory:
            for dataset_path in self.get_output_fnames():
                try:
                    shutil.move( dataset_path.false_path, dataset_path.real_path )
                    log.debug( "finish(): Moved %s to %s" % ( dataset_path.false_path, dataset_path.real_path ) )
                except ( IOError, OSError ):
                    # this can happen if Galaxy is restarted during the job's
                    # finish method - the false_path file has already moved,
                    # and when the job is recovered, it won't be found.
                    if os.path.exists( dataset_path.real_path ) and os.stat( dataset_path.real_path ).st_size > 0:
                        log.warning( "finish(): %s not found, but %s is not empty, so it will be used instead" % ( dataset_path.false_path, dataset_path.real_path ) )
                    else:
                        self.fail( "Job %s's output dataset(s) could not be read" % job.id )
                        return
        job_context = ExpressionContext( dict( stdout = stdout, stderr = stderr ) )
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            context = self.get_dataset_finish_context( job_context, dataset_assoc.dataset.dataset )
            #should this also be checking library associations? - can a library item be added from a history before the job has ended? - lets not allow this to occur
            for dataset in dataset_assoc.dataset.dataset.history_associations + dataset_assoc.dataset.dataset.library_associations: #need to update all associated output hdas, i.e. history was shared with job running
                dataset.blurb = 'done'
                dataset.peek  = 'no peek'
                dataset.info  = context['stdout'] + context['stderr']
                dataset.set_size()
                if context['stderr']:
                    dataset.blurb = "error"
                elif dataset.has_data():
                    # If the tool was expected to set the extension, attempt to retrieve it
                    if dataset.ext == 'auto':
                        dataset.extension = context.get( 'ext', 'data' )
                        dataset.init_meta( copy_from=dataset )
                    #if a dataset was copied, it won't appear in our dictionary:
                    #either use the metadata from originating output dataset, or call set_meta on the copies
                    #it would be quicker to just copy the metadata from the originating output dataset, 
                    #but somewhat trickier (need to recurse up the copied_from tree), for now we'll call set_meta()
                    if not self.external_output_metadata.external_metadata_set_successfully( dataset, self.sa_session ):
                        # Only set metadata values if they are missing...
                        dataset.set_meta( overwrite = False )
                    else:
                        #load metadata from file
                        #we need to no longer allow metadata to be edited while the job is still running,
                        #since if it is edited, the metadata changed on the running output will no longer match
                        #the metadata that was stored to disk for use via the external process, 
                        #and the changes made by the user will be lost, without warning or notice
                        dataset.metadata.from_JSON_dict( self.external_output_metadata.get_output_filenames_by_dataset( dataset, self.sa_session ).filename_out )
                    try:
                        assert context.get( 'line_count', None ) is not None
                        if ( not dataset.datatype.composite_type and dataset.dataset.is_multi_byte() ) or self.tool.is_multi_byte:
                            dataset.set_peek( line_count=context['line_count'], is_multi_byte=True )
                        else:
                            dataset.set_peek( line_count=context['line_count'] )
                    except:
                        if ( not dataset.datatype.composite_type and dataset.dataset.is_multi_byte() ) or self.tool.is_multi_byte:
                            dataset.set_peek( is_multi_byte=True )
                        else:
                            dataset.set_peek()
                    try:
                        # set the name if provided by the tool
                        dataset.name = context['name']
                    except:
                        pass
                else:
                    dataset.blurb = "empty"
                    if dataset.ext == 'auto':
                        dataset.extension = 'txt'
                self.sa_session.add( dataset )
                self.sa_session.flush()
            if context['stderr']:
                dataset_assoc.dataset.dataset.state = model.Dataset.states.ERROR
            else:
                dataset_assoc.dataset.dataset.state = model.Dataset.states.OK
            # If any of the rest of the finish method below raises an
            # exception, the fail method will run and set the datasets to
            # ERROR.  The user will never see that the datasets are in error if
            # they were flushed as OK here, since upon doing so, the history
            # panel stops checking for updates.  So allow the
            # self.sa_session.flush() at the bottom of this method set
            # the state instead.
        
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
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] ) # why not re-use self.param_dict here? ##dunno...probably should, this causes tools.parameters.basic.UnvalidatedValue to be used in following methods instead of validated and transformed values during i.e. running workflows
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        # Check for and move associated_files
        self.tool.collect_associated_files(out_data, self.working_directory)
        # Create generated output children and primary datasets and add to param_dict
        collected_datasets = {'children':self.tool.collect_child_datasets(out_data),'primary':self.tool.collect_primary_datasets(out_data)}
        param_dict.update({'__collected_datasets__':collected_datasets})
        # Certain tools require tasks to be completed after job execution
        # ( this used to be performed in the "exec_after_process" hook, but hooks are deprecated ).
        self.tool.exec_after_process( self.queue.app, inp_data, out_data, param_dict, job = job )
        # Call 'exec_after_process' hook
        self.tool.call_hook( 'exec_after_process', self.queue.app, inp_data=inp_data, 
                             out_data=out_data, param_dict=param_dict, 
                             tool=self.tool, stdout=stdout, stderr=stderr )
        job.command_line = self.command_line
        for pja in job.post_job_actions:
            ActionBox.execute(self.app, self.sa_session, pja.post_job_action, job)
        # fix permissions
        for path in [ dp.real_path for dp in self.get_output_fnames() ]:
            util.umask_fix_perms( path, self.app.config.umask, 0666, self.app.config.gid )
        self.sa_session.flush()
        log.debug( 'job %d ended' % self.job_id )
        self.cleanup()
        
    def cleanup( self ):
        # remove temporary files
        try:
            for fname in self.extra_filenames:
                os.remove( fname )
            if self.working_directory is not None:
                shutil.rmtree( self.working_directory )
            if self.app.config.set_metadata_externally:
                self.external_output_metadata.cleanup_external_metadata( self.sa_session )
        except:
            log.exception( "Unable to cleanup job %d" % self.job_id )
        
    def get_command_line( self ):
        return self.command_line
    
    def get_session_id( self ):
        return self.session_id

    def get_input_fnames( self ):
        job = self.sa_session.query( model.Job ).get( self.job_id )
        filenames = []
        for da in job.input_datasets: #da is JobToInputDatasetAssociation object
            if da.dataset:
                filenames.append( da.dataset.file_name )
                #we will need to stage in metadata file names also
                #TODO: would be better to only stage in metadata files that are actually needed (found in command line, referenced in config files, etc.)
                for key, value in da.dataset.metadata.items():
                    if isinstance( value, model.MetadataFile ):
                        filenames.append( value.file_name )
        return filenames

    def get_output_fnames( self ):
        if self.output_paths is not None:
            return self.output_paths

        class DatasetPath( object ):
            def __init__( self, dataset_id, real_path, false_path = None ):
                self.dataset_id = dataset_id
                self.real_path = real_path
                self.false_path = false_path
            def __str__( self ):
                if self.false_path is None:
                    return self.real_path
                else:
                    return self.false_path

        job = self.sa_session.query( model.Job ).get( self.job_id )
        if self.app.config.outputs_to_working_directory:
            self.output_paths = []
            for name, data in [ ( da.name, da.dataset.dataset ) for da in job.output_datasets + job.output_library_datasets ]:
                false_path = os.path.abspath( os.path.join( self.working_directory, "galaxy_dataset_%d.dat" % data.id ) )
                self.output_paths.append( DatasetPath( data.id, data.file_name, false_path ) )
        else:
            self.output_paths = [ DatasetPath( da.dataset.dataset.id, da.dataset.file_name ) for da in job.output_datasets + job.output_library_datasets ]
        return self.output_paths

    def get_output_file_id( self, file ):
        if self.output_paths is None:
            self.get_output_fnames()
        for dp in self.output_paths:
            if self.app.config.outputs_to_working_directory and os.path.basename( dp.false_path ) == file:
                return dp.dataset_id
            elif os.path.basename( dp.real_path ) == file:
                return dp.dataset_id
        return None

    def get_tool_provided_job_metadata( self ):
        if self.tool_provided_job_metadata is not None:
            return self.tool_provided_job_metadata

        # Look for JSONified job metadata
        self.tool_provided_job_metadata = []
        meta_file = os.path.join( self.working_directory, TOOL_PROVIDED_JOB_METADATA_FILE )
        if os.path.exists( meta_file ):
            for line in open( meta_file, 'r' ):
                try:
                    line = from_json_string( line )
                    assert 'type' in line
                except:
                    log.exception( '(%s) Got JSON data from tool, but data is improperly formatted or no "type" key in data' % self.job_id )
                    log.debug( 'Offending data was: %s' % line )
                    continue
                # Set the dataset id if it's a dataset entry and isn't set.
                # This isn't insecure.  We loop the job's output datasets in
                # the finish method, so if a tool writes out metadata for a
                # dataset id that it doesn't own, it'll just be ignored.
                if line['type'] == 'dataset' and 'dataset_id' not in line:
                    try:
                        line['dataset_id'] = self.get_output_file_id( line['dataset'] )
                    except KeyError:
                        log.warning( '(%s) Tool provided job dataset-specific metadata without specifying a dataset' % self.job_id )
                        continue
                self.tool_provided_job_metadata.append( line )
        return self.tool_provided_job_metadata

    def get_dataset_finish_context( self, job_context, dataset ):
        for meta in self.get_tool_provided_job_metadata():
            if meta['type'] == 'dataset' and meta['dataset_id'] == dataset.id:
                return ExpressionContext( meta, job_context )
        return job_context

    def check_output_sizes( self ):
        sizes = []
        output_paths = self.get_output_fnames()
        for outfile in [ str( o ) for o in output_paths ]:
            sizes.append( ( outfile, os.stat( outfile ).st_size ) )
        return sizes

    def setup_external_metadata( self, exec_dir = None, tmp_dir = None, dataset_files_path = None, config_root = None, datatypes_config = None, set_extension = True, **kwds ):
        # extension could still be 'auto' if this is the upload tool.
        job = self.sa_session.query( model.Job ).get( self.job_id )
        if set_extension:
            for output_dataset_assoc in job.output_datasets:
                if output_dataset_assoc.dataset.ext == 'auto':
                    context = self.get_dataset_finish_context( dict(), output_dataset_assoc.dataset.dataset )
                    output_dataset_assoc.dataset.extension = context.get( 'ext', 'data' )
            self.sa_session.flush()
        if tmp_dir is None:
            #this dir should should relative to the exec_dir
            tmp_dir = self.app.config.new_file_path
        if dataset_files_path is None:
            dataset_files_path = self.app.model.Dataset.file_path
        if config_root is None:
            config_root = self.app.config.root
        if datatypes_config is None:
            datatypes_config = self.app.config.datatypes_config
        return self.external_output_metadata.setup_external_metadata( [ output_dataset_assoc.dataset for output_dataset_assoc in job.output_datasets ],
                                                                      self.sa_session,
                                                                      exec_dir = exec_dir,
                                                                      tmp_dir = tmp_dir,
                                                                      dataset_files_path = dataset_files_path,
                                                                      config_root = config_root,
                                                                      datatypes_config = datatypes_config,
                                                                      job_metadata = os.path.join( self.working_directory, TOOL_PROVIDED_JOB_METADATA_FILE ),
                                                                      **kwds )

    @property
    def user( self ):
        job = self.sa_session.query( model.Job ).get( self.job_id )
        if job.user is not None:
            return job.user.email
        elif job.galaxy_session is not None and job.galaxy_session.user is not None:
            return job.galaxy_session.user.email
        elif job.history is not None and job.history.user is not None:
            return job.history.user.email
        elif job.galaxy_session is not None:
            return 'anonymous@' + job.galaxy_session.remote_addr.split()[-1]
        else:
            return 'anonymous@unknown'

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
            elif runner_name == "drmaa":
                import runners.drmaa
                self.job_runners[runner_name] = runners.drmaa.DRMAAJobRunner( app )
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
        self.sa_session = app.model.context
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
                ( job_id, error_msg ) = self.queue.get_nowait()
                if job_id is self.STOP_SIGNAL:
                    return
                # Append to watch queue
                jobs.append( ( job_id, error_msg ) )
        except Empty:
            pass  

        for job_id, error_msg in jobs:
            job = self.sa_session.query( model.Job ).get( job_id )
            self.sa_session.refresh( job )
            # if desired, error the job so we can inform the user.
            if error_msg is not None:
                job.state = job.states.ERROR
                job.info = error_msg
            else:
                job.state = job.states.DELETED
            self.sa_session.add( job )
            self.sa_session.flush()
            # if job is in JobQueue or FooJobRunner's put method,
            # job_runner_name will be unset and the job will be dequeued due to
            # state change above
            if job.job_runner_name is not None:
                # tell the dispatcher to stop the job
                self.dispatcher.stop( job )

    def put( self, job_id, error_msg=None ):
        self.queue.put( ( job_id, error_msg ) )

    def shutdown( self ):
        """Attempts to gracefully shut down the worker thread"""
        if self.parent_pid != os.getpid():
            # We're not the real job queue, do nothing
            return
        else:
            log.info( "sending stop signal to worker thread" )
            self.running = False
            self.queue.put( ( self.STOP_SIGNAL, None ) )
            self.sleeper.wake()
            log.info( "job stopper stopped" )

class NoopQueue( object ):
    """
    Implements the JobQueue / JobStopQueue interface but does nothing
    """
    def put( self, *args ):
        return
    def shutdown( self ):
        return


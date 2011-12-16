import logging, threading, sys, os, time, traceback, shutil

import galaxy
from galaxy import util, model
from galaxy.datatypes.tabular import *
from galaxy.datatypes.interval import *
# tabular/interval imports appear to be unused.  Clean up?
from galaxy.datatypes import metadata
from galaxy.util.json import from_json_string
from galaxy.util.expressions import ExpressionContext
from galaxy.jobs.actions.post import ActionBox

from sqlalchemy.sql.expression import and_, or_

import pkg_resources
pkg_resources.require( "PasteDeploy" )

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
            if self.app.config.enable_beta_job_managers:
                from galaxy.jobs.deferred import DeferredJobQueue
                self.deferred_job_queue = DeferredJobQueue( app )
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
        ## This and jobs_to_check[] are closest to a "Job Queue"
        self.waiting_jobs = []
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
        model = self.app.model # DBTODO Why?
        for job in self.sa_session.query( model.Job ).filter( model.Job.state == model.Job.states.NEW ):
            if job.tool_id not in self.app.toolbox.tools_by_id:
                log.warning( "Tool '%s' removed from tool config, unable to recover job: %s" % ( job.tool_id, job.id ) )
                JobWrapper( job, self ).fail( 'This tool was disabled before the job completed.  Please contact your Galaxy administrator, or' )
            else:
                log.debug( "no runner: %s is still in new state, adding to the jobs queue" %job.id )
                self.queue.put( ( job.id, job.tool_id ) )
        for job in self.sa_session.query( model.Job ).enable_eagerloads( False ).filter( ( model.Job.state == model.Job.states.RUNNING ) | ( model.Job.state == model.Job.states.QUEUED ) ):
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
        jobs_to_check = []
        if self.track_jobs_in_database:
            # Clear the session so we get fresh states for job and all datasets
            self.sa_session.expunge_all()
            # Fetch all new jobs
            jobs_to_check = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                                .filter( model.Job.state == model.Job.states.NEW ).all()
        else:
            # Get job objects and append to watch queue for any which were
            # previously waiting
            for job_id in self.waiting_jobs:
                jobs_to_check.append( self.sa_session.query( model.Job ).get( job_id ) )
            try:
                while 1:
                    message = self.queue.get_nowait()
                    if message is self.STOP_SIGNAL:
                        return
                    # Unpack the message
                    job_id, tool_id = message
                    # Get the job object and append to watch queue
                    jobs_to_check.append( self.sa_session.query( model.Job ).get( job_id ) )
            except Empty:
                pass
        # Iterate over new and waiting jobs and look for any that are
        # ready to run
        new_waiting_jobs = []
        for job in jobs_to_check:
            try:
                # Check the job's dependencies, requeue if they're not done
                job_state = self.__check_if_ready_to_run( job )
                if job_state == JOB_WAIT:
                    if not self.track_jobs_in_database:
                        new_waiting_jobs.append( job.id )
                elif job_state == JOB_INPUT_ERROR:
                    log.info( "job %d unable to run: one or more inputs in error state" % job.id )
                elif job_state == JOB_INPUT_DELETED:
                    log.info( "job %d unable to run: one or more inputs deleted" % job.id )
                elif job_state == JOB_READY:
                    if self.job_lock:
                        log.info( "Job dispatch attempted for %s, but prevented by administrative lock." % job.id )
                        if not self.track_jobs_in_database:
                            new_waiting_jobs.append( job.id )
                    else:
                        self.dispatcher.put( JobWrapper( job, self ) )
                        log.info( "job %d dispatched" % job.id )
                elif job_state == JOB_DELETED:
                    log.info( "job %d deleted by user while still queued" % job.id )
                elif job_state == JOB_ADMIN_DELETED:
                    log.info( "job %d deleted by admin while still queued" % job.id )
                else:
                    log.error( "unknown job state '%s' for job %d" % ( job_state, job.id ) )
                    if not self.track_jobs_in_database:
                        new_waiting_jobs.append( job.id )
            except Exception:
                log.exception( "failure running job %d" % job.id )
        # Update the waiting list
        self.waiting_jobs = new_waiting_jobs
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
        elif self.app.config.enable_quotas:
            quota = self.app.quota_agent.get_quota( job.user )
            if quota is not None:
                try:
                    usage = self.app.quota_agent.get_usage( user=job.user, history=job.history )
                    if usage > quota:
                        return JOB_WAIT
                except AssertionError, e:
                    pass # No history, should not happen with an anon user
        for dataset_assoc in job.input_datasets + job.input_library_datasets:
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
            elif idata.state == idata.states.FAILED_METADATA:
                JobWrapper( job, self ).fail( "input data %d failed to properly set metadata" % ( idata.hid ) )
                return JOB_INPUT_ERROR
            elif idata.state != idata.states.OK and not ( idata.state == idata.states.SETTING_METADATA and job.tool_id is not None and job.tool_id == self.app.datatypes_registry.set_external_metadata_tool.id ):
                # need to requeue
                return JOB_WAIT
        return self.__check_user_jobs( job )

    def __check_user_jobs( self, job ):
        if not self.app.config.user_job_limit:
            return JOB_READY
        if job.user:
            count = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                        .filter( and_( model.Job.user_id == job.user.id,
                                       or_( model.Job.state == model.Job.states.RUNNING,
                                            model.Job.state == model.Job.states.QUEUED ) ) ).count()
        elif job.galaxy_session:
            count = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                        .filter( and_( model.Job.session_id == job.galaxy_session.id,
                                       or_( model.Job.state == model.Job.states.RUNNING,
                                            model.Job.state == model.Job.states.QUEUED ) ) ).count()
        else:
            log.warning( 'Job %s is not associated with a user or session so job concurrency limit cannot be checked.' % job.id )
            return JOB_READY
        if count >= self.app.config.user_job_limit:
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
    Wraps a 'model.Job' with convenience methods for running processes and
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
        # Tool versioning variables
        self.version_string_cmd = None
        self.version_string = ""
        self.galaxy_lib_dir = None
        # With job outputs in the working directory, we need the working
        # directory to be set before prepare is run, or else premature deletion
        # and job recovery fail.
        # Attempt to put the working directory in the same store as the output dataset(s)
        store_name = None
        da = None
        if job.output_datasets:
            da = job.output_datasets[0]
        elif job.output_library_datasets:
            da = job.output_library_datasets[0]
        if da is not None:
            store_name = self.app.object_store.store_name(da.dataset.id)
        # Create the working dir if necessary
        if not self.app.object_store.exists(self.job_id, base_dir='job_work', dir_only=True, extra_dir=str(self.job_id)):
            self.app.object_store.create(self.job_id, base_dir='job_work', dir_only=True, extra_dir=str(self.job_id), store_name=store_name)
        self.working_directory = self.app.object_store.get_filename(self.job_id, base_dir='job_work', dir_only=True, extra_dir=str(self.job_id))
        log.debug('(%s) Working directory for job is: %s' % (self.job_id, self.working_directory))
        self.output_paths = None
        self.output_dataset_paths = None
        self.tool_provided_job_metadata = None
        # Wrapper holding the info required to restore and clean up from files used for setting metadata externally
        self.external_output_metadata = metadata.JobExternalOutputMetadataWrapper( job )

    def get_job_runner( self ):
        return self.tool.job_runner

    def get_job( self ):
        return self.sa_session.query( model.Job ).get( self.job_id )

    def get_id_tag(self):
        # For compatability with drmaa, which uses job_id right now, and TaskWrapper
        return str(self.job_id)

    def get_param_dict( self ):
        """
        Restore the dictionary of parameters from the database.
        """
        job = self.get_job()
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        return param_dict

    def get_version_string_path( self ):
        return os.path.abspath(os.path.join(self.app.config.new_file_path, "GALAXY_VERSION_STRING_%s" % self.job_id))

    def prepare( self ):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        self.sa_session.expunge_all() #this prevents the metadata reverting that has been seen in conjunction with the PBS job runner
        if not os.path.exists( self.working_directory ):
            os.mkdir( self.working_directory )
        # Restore parameters from the database
        job = self.get_job()
        if job.user is None and job.galaxy_session is None:
            raise Exception( 'Job %s has no user and no session.' % job.id )
        incoming = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        incoming = self.tool.params_from_strings( incoming, self.app )
        # Do any validation that could not be done at job creation
        self.tool.handle_unvalidated_param_values( incoming, self.app )
        # Restore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )

        # Set up output dataset association for export history jobs. Because job
        # uses a Dataset rather than an HDA or LDA, it's necessary to set up a
        # fake dataset association that provides the needed attributes for
        # preparing a job.
        class FakeDatasetAssociation ( object ):
            def __init__( self, dataset=None ):
                self.dataset = dataset
                self.file_name = dataset.file_name
                self.metadata = dict()
                self.children = []
        jeha = self.sa_session.query( model.JobExportHistoryArchive ).filter_by( job=job ).first()
        if jeha:
            out_data[ "output_file" ] = FakeDatasetAssociation( dataset=jeha.dataset )
        # These can be passed on the command line if wanted as $userId $userEmail
        if job.history and job.history.user: # check for anonymous user!
            userId = '%d' % job.history.user.id
            userEmail = str(job.history.user.email)
        else:
            userId = 'Anonymous'
            userEmail = 'Anonymous'
        incoming['__user_id__'] = incoming['userId'] = userId
        incoming['__user_email__'] = incoming['userEmail'] = userEmail
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
        # Shell fragment to inject dependencies
        if self.app.config.use_tool_dependencies:
            self.dependency_shell_commands = self.tool.build_dependency_shell_commands()
        else:
            self.dependency_shell_commands = None
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
        self.version_string_cmd = self.tool.version_string_cmd
        return extra_filenames

    def fail( self, message, exception=False ):
        """
        Indicate job failure by setting state and message on all output
        datasets.
        """
        job = self.get_job()
        self.sa_session.refresh( job )
        # if the job was deleted, don't fail it
        if not job.state == job.states.DELETED:
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
                dataset.dataset.set_total_size()
                if dataset.ext == 'auto':
                    dataset.extension = 'data'
                # Update (non-library) job output datasets through the object store
                if dataset not in job.output_library_datasets:
                    self.app.object_store.update_from_file(dataset.id, create=True)
                self.sa_session.add( dataset )
                self.sa_session.flush()
            job.state = job.states.ERROR
            job.command_line = self.command_line
            job.info = message
            self.sa_session.add( job )
            self.sa_session.flush()
        #Perform email action even on failure.
        for pja in [x for x in job.post_job_actions if x.action_type == "EmailAction"]:
            ActionBox.execute(self.app, self.sa_session, pja.post_job_action, job)
        # If the job was deleted, call tool specific fail actions (used for e.g. external metadata) and clean up
        if self.tool:
            self.tool.job_failed( self, message, exception )
        if self.app.config.cleanup_job == 'always' or (self.app.config.cleanup_job == 'onsuccess' and job.state == job.states.DELETED):
            self.cleanup()

    def change_state( self, state, info = False ):
        job = self.get_job()
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
        job = self.get_job()
        self.sa_session.refresh( job )
        return job.state

    def set_runner( self, runner_url, external_id ):
        job = self.get_job()
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
        job = self.get_job()
        # if the job was deleted, don't finish it
        if job.state == job.states.DELETED or job.state == job.states.ERROR:
            #ERROR at this point means the job was deleted by an administrator.
            return self.fail( job.info )
        if stderr:
            job.state = job.states.ERROR
        else:
            job.state = job.states.OK
        if self.version_string_cmd:
            version_filename = self.get_version_string_path()
            if os.path.exists(version_filename):
                self.version_string = open(version_filename).read()
                os.unlink(version_filename)

        if self.app.config.outputs_to_working_directory and not self.__link_file_check():
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
                        return self.fail( "Job %s's output dataset(s) could not be read" % job.id )
        job_context = ExpressionContext( dict( stdout = stdout, stderr = stderr ) )
        job_tool = self.app.toolbox.tools_by_id.get( job.tool_id, None )
        def in_directory( file, directory ):
            # Make both absolute.
            directory = os.path.realpath( directory )
            file = os.path.realpath( file )

            #Return true, if the common prefix of both is equal to directory
            #e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
            return os.path.commonprefix( [ file, directory ] ) == directory
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            context = self.get_dataset_finish_context( job_context, dataset_assoc.dataset.dataset )
            #should this also be checking library associations? - can a library item be added from a history before the job has ended? - lets not allow this to occur
            for dataset in dataset_assoc.dataset.dataset.history_associations + dataset_assoc.dataset.dataset.library_associations: #need to update all associated output hdas, i.e. history was shared with job running
                #
                # If HDA is to be copied from the working directory, do it now so that other attributes are correctly set.
                #
                if isinstance( dataset, model.HistoryDatasetAssociation ):
                    joda = self.sa_session.query( model.JobToOutputDatasetAssociation ).filter_by( job=job, dataset=dataset ).first()
                    if joda and job_tool:
                        hda_tool_output = job_tool.outputs.get( joda.name, None )
                        if hda_tool_output and hda_tool_output.from_work_dir:
                            # Copy from working dir to HDA.
                            source_file = os.path.join( os.path.abspath( self.working_directory ), hda_tool_output.from_work_dir )
                            if in_directory( source_file, self.working_directory ):
                                try:
                                    shutil.move( source_file, dataset.file_name )
                                    log.debug( "finish(): Moved %s to %s as directed by from_work_dir" % ( source_file, dataset.file_name ) )
                                except ( IOError, OSError ):
                                    log.debug( "finish(): Could not move %s to %s as directed by from_work_dir" % ( source_file, dataset.file_name ) )
                            else:
                                # Security violation.
                                log.exception( "from_work_dir specified a location not in the working directory: %s, %s" % ( source_file, self.working_directory ) )

                dataset.blurb = 'done'
                dataset.peek  = 'no peek'
                dataset.info = ( dataset.info  or '' ) + context['stdout'] + context['stderr']
                dataset.tool_version = self.version_string
                dataset.set_size()
                # Update (non-library) job output datasets through the object store
                if dataset not in job.output_library_datasets:
                    self.app.object_store.update_from_file(dataset.id, create=True)
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
                    if not self.app.config.set_metadata_externally or \
                     ( not self.external_output_metadata.external_metadata_set_successfully( dataset, self.sa_session ) \
                       and self.app.config.retry_metadata_internally ):
                        dataset.set_meta( overwrite = False )
                    elif not self.external_output_metadata.external_metadata_set_successfully( dataset, self.sa_session ) and not context['stderr']:
                        dataset._state = model.Dataset.states.FAILED_METADATA
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

        for pja in job.post_job_actions:
            ActionBox.execute(self.app, self.sa_session, pja.post_job_action, job)
        # Flush all the dataset and job changes above.  Dataset state changes
        # will now be seen by the user.
        self.sa_session.flush()
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
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
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

        bytes = 0
        # Once datasets are collected, set the total dataset size (includes extra files)
        for dataset_assoc in job.output_datasets:
            dataset_assoc.dataset.dataset.set_total_size()
            bytes += dataset_assoc.dataset.dataset.get_total_size()

        if job.user:
            job.user.total_disk_usage += bytes

        # fix permissions
        for path in [ dp.real_path for dp in self.get_output_fnames() ]:
            util.umask_fix_perms( path, self.app.config.umask, 0666, self.app.config.gid )
        self.sa_session.flush()
        log.debug( 'job %d ended' % self.job_id )
        if self.app.config.cleanup_job == 'always' or ( not stderr and self.app.config.cleanup_job == 'onsuccess' ):
            self.cleanup()

    def cleanup( self ):
        # remove temporary files
        try:
            for fname in self.extra_filenames:
                os.remove( fname )
            if self.working_directory is not None and os.path.isdir( self.working_directory ):
                shutil.rmtree( self.working_directory )
            if self.app.config.set_metadata_externally:
                self.external_output_metadata.cleanup_external_metadata( self.sa_session )
            galaxy.tools.imp_exp.JobExportHistoryArchiveWrapper( self.job_id ).cleanup_after_job( self.sa_session )
            galaxy.tools.imp_exp.JobImportHistoryArchiveWrapper( self.job_id ).cleanup_after_job( self.sa_session )
        except:
            log.exception( "Unable to cleanup job %d" % self.job_id )

    def get_command_line( self ):
        return self.command_line

    def get_session_id( self ):
        return self.session_id

    def get_input_dataset_fnames( self,  ds ):
        filenames = []
        filenames = [ ds.file_name ]
        #we will need to stage in metadata file names also
        #TODO: would be better to only stage in metadata files that are actually needed (found in command line, referenced in config files, etc.)
        for key, value in ds.metadata.items():
            if isinstance( value, model.MetadataFile ):
                filenames.append( value.file_name )
        return filenames

    def get_input_fnames( self ):
        job = self.get_job()
        filenames = []
        for da in job.input_datasets + job.input_library_datasets: #da is JobToInputDatasetAssociation object
            if da.dataset:
                filenames.extend(self.get_input_dataset_fnames(da.dataset))
        return filenames

    def get_output_fnames( self ):
        if self.output_paths is None:
            self.compute_outputs()
        return self.output_paths

    def get_output_datasets_and_fnames( self ):
        if self.output_dataset_paths is None:
            self.compute_outputs()
        return self.output_dataset_paths

    def compute_outputs( self ) :
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
        job = self.get_job()
        # Job output datasets are combination of output datasets, library datasets, and jeha datasets.
        jeha = self.sa_session.query( model.JobExportHistoryArchive ).filter_by( job=job ).first()
        jeha_false_path = None
        if self.app.config.outputs_to_working_directory:
            self.output_paths = []
            self.output_dataset_paths = {}
            for name, data in [ ( da.name, da.dataset.dataset ) for da in job.output_datasets + job.output_library_datasets ]:
                false_path = os.path.abspath( os.path.join( self.working_directory, "galaxy_dataset_%d.dat" % data.id ) )
                dsp = DatasetPath( data.id, data.file_name, false_path )
                self.output_paths.append( dsp )
                self.output_dataset_paths[name] = data,  dsp
            if jeha:
                jeha_false_path = os.path.abspath( os.path.join( self.working_directory, "galaxy_dataset_%d.dat" % jeha.dataset.id ) )
        else:
            results = [ (da.name,  da.dataset,  DatasetPath( da.dataset.dataset.id, da.dataset.file_name )) for da in job.output_datasets + job.output_library_datasets ]
            self.output_paths = [t[2] for t in results]
            self.output_dataset_paths = dict([(t[0],  t[1:]) for t in results])
        if jeha:
            dsp = DatasetPath( jeha.dataset.id, jeha.dataset.file_name, jeha_false_path )
            self.output_paths.append( dsp )
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
            if os.path.exists( outfile ):
                sizes.append( ( outfile, os.stat( outfile ).st_size ) )
            else:
                sizes.append( ( outfile, 0 ) )
        return sizes

    def setup_external_metadata( self, exec_dir = None, tmp_dir = None, dataset_files_path = None, config_root = None, datatypes_config = None, set_extension = True, **kwds ):
        # extension could still be 'auto' if this is the upload tool.
        job = self.get_job()
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
            datatypes_config = self.app.datatypes_registry.to_xml_file()
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
        job = self.get_job()
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

    def __link_file_check( self ):
        """ outputs_to_working_directory breaks library uploads where data is
        linked.  This method is a hack that solves that problem, but is
        specific to the upload tool and relies on an injected job param.  This
        method should be removed ASAP and replaced with some properly generic
        and stateful way of determining link-only datasets. -nate
        """
        job = self.get_job()
        param_dict = job.get_param_values( self.app )
        return self.tool.id == 'upload1' and param_dict.get( 'link_data_only', None ) == 'link_to_files'

class TaskWrapper(JobWrapper):
    """
    Extension of JobWrapper intended for running tasks.
    Should be refactored into a generalized executable unit wrapper parent, then jobs and tasks.
    """
    # Abstract this to be more useful for running tasks that *don't* necessarily compose a job.

    def __init__(self, task, queue):
        super(TaskWrapper, self).__init__(task.job, queue)
        self.task_id = task.id
        self.working_directory = task.working_directory
        if task.prepare_input_files_cmd is not None:
            self.prepare_input_files_cmds = [ task.prepare_input_files_cmd ]
        else:
            self.prepare_input_files_cmds = None
        self.status = task.states.NEW

    def get_job( self ):
        if self.job_id:
            return self.sa_session.query( model.Job ).get( self.job_id )
        else:
            return None

    def get_task( self ):
        return self.sa_session.query(model.Task).get(self.task_id)

    def get_id_tag(self):
        # For compatibility with drmaa job runner and TaskWrapper, instead of using job_id directly
        return "%s_%s" % (self.job_id, self.task_id)

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
        # Restore parameters from the database
        job = self.get_job()
        task = self.get_task()
        if job.user is None and job.galaxy_session is None:
            raise Exception( 'Job %s has no user and no session.' % job.id )
        incoming = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        incoming = self.tool.params_from_strings( incoming, self.app )
        # Do any validation that could not be done at job creation
        self.tool.handle_unvalidated_param_values( incoming, self.app )
        # Restore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )
        # DBTODO New method for generating command line for a task?
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
        fnames = {}
        for v in self.get_input_fnames():
            fnames[v] = os.path.join(self.working_directory, os.path.basename(v))
        for dp in [x.real_path for x in self.get_output_fnames()]:
            fnames[dp] = os.path.join(self.working_directory, os.path.basename(dp))
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
        # HACK, Fix this when refactored.
        for k, v in fnames.iteritems():
            self.command_line = self.command_line.replace(k, v)
        # FIXME: for now, tools get Galaxy's lib dir in their path
        if self.command_line and self.command_line.startswith( 'python' ):
            self.galaxy_lib_dir = os.path.abspath( "lib" ) # cwd = galaxy root
        # Shell fragment to inject dependencies
        if self.app.config.use_tool_dependencies:
            self.dependency_shell_commands = self.tool.build_dependency_shell_commands()
        else:
            self.dependency_shell_commands = None
        # We need command_line persisted to the db in order for Galaxy to re-queue the job
        # if the server was stopped and restarted before the job finished
        task.command_line = self.command_line
        self.sa_session.add( task )
        self.sa_session.flush()
        # # Return list of all extra files
        extra_filenames = config_filenames
        if param_filename is not None:
            extra_filenames.append( param_filename )
        self.param_dict = param_dict
        self.extra_filenames = extra_filenames
        self.status = 'prepared'
        return extra_filenames

    def fail( self, message, exception=False ):
        log.error("TaskWrapper Failure %s" % message)
        self.status = 'error'
        # How do we want to handle task failure?  Fail the job and let it clean up?

    def change_state( self, state, info = False ):
        task = self.get_task()
        self.sa_session.refresh( task )
        if info:
            task.info = info
        task.state = state
        self.sa_session.add( task )
        self.sa_session.flush()

    def get_state( self ):
        task = self.get_task()
        self.sa_session.refresh( task )
        return task.state

    def set_runner( self, runner_url, external_id ):
        task = self.get_task()
        self.sa_session.refresh( task )
        task.task_runner_name = runner_url
        task.task_runner_external_id = external_id
        # DBTODO Check task job_runner_stuff
        self.sa_session.add( task )
        self.sa_session.flush()

    def finish( self, stdout, stderr ):
        # DBTODO integrate previous finish logic.
        # Simple finish for tasks.  Just set the flag OK.
        log.debug( 'task %s for job %d ended' % (self.task_id, self.job_id) )
        """
        Called to indicate that the associated command has been run. Updates
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files.
        """
        # default post job setup_external_metadata
        self.sa_session.expunge_all()
        task = self.get_task()
        # if the job was deleted, don't finish it
        if task.state == task.states.DELETED:
            if self.app.config.cleanup_job in ( 'always', 'onsuccess' ):
                self.cleanup()
            return
        elif task.state == task.states.ERROR:
            # Job was deleted by an administrator
            self.fail( task.info )
            return
        if stderr:
            task.state = task.states.ERROR
        else:
            task.state = task.states.OK
        # Save stdout and stderr
        if len( stdout ) > 32768:
            log.error( "stdout for task %d is greater than 32K, only first part will be logged to database" % task.id )
        task.stdout = stdout[:32768]
        if len( stderr ) > 32768:
            log.error( "stderr for job %d is greater than 32K, only first part will be logged to database" % task.id )
        task.stderr = stderr[:32768]
        task.command_line = self.command_line
        self.sa_session.flush()
        log.debug( 'task %d ended' % self.task_id )

    def cleanup( self ):
        # There is no task cleanup.  The job cleans up for all tasks.
        pass

    def get_command_line( self ):
        return self.command_line

    def get_session_id( self ):
        return self.session_id

    def get_output_file_id( self, file ):
        # There is no permanent output file for tasks.
        return None

    def get_tool_provided_job_metadata( self ):
        # DBTODO Handle this as applicable for tasks.
        return None

    def get_dataset_finish_context( self, job_context, dataset ):
        # Handled at the parent job level.  Do nothing here.
        pass

    def check_output_sizes( self ):
        sizes = []
        output_paths = self.get_output_fnames()
        for outfile in [ str( o ) for o in output_paths ]:
            if os.path.exists( outfile ):
                sizes.append( ( outfile, os.stat( outfile ).st_size ) )
            else:
                sizes.append( ( outfile, 0 ) )
        return sizes

    def setup_external_metadata( self, exec_dir = None, tmp_dir = None, dataset_files_path = None, config_root = None, datatypes_config = None, set_extension = True, **kwds ):
        # There is no metadata setting for tasks.  This is handled after the merge, at the job level.
        return ""

class DefaultJobDispatcher( object ):
    def __init__( self, app ):
        self.app = app
        self.job_runners = {}
        start_job_runners = ["local"]
        if app.config.start_job_runners is not None:
            start_job_runners.extend( app.config.start_job_runners.split(",") )
        if app.config.use_tasked_jobs:
            start_job_runners.append("tasks")
        for name in start_job_runners:
            self._load_plugin( name )

    def _load_plugin( self, name ):
        module_name = 'galaxy.jobs.runners.' + name
        try:
            module = __import__( module_name )
        except:
            log.exception( 'Job runner is not loadable: %s' % module_name )
            return
        for comp in module_name.split( "." )[1:]:
            module = getattr( module, comp )
        if '__all__' not in dir( module ):
            log.error( 'Runner "%s" does not contain a list of exported classes in __all__' % module_name )
            return
        for obj in module.__all__:
            display_name = ':'.join( ( module_name, obj ) )
            runner = getattr( module, obj )
            self.job_runners[name] = runner( self.app )
            log.debug( 'Loaded job runner: %s' % display_name )

    def __get_runner_name( self, job_wrapper ):
        if self.app.config.use_tasked_jobs and job_wrapper.tool.parallelism is not None and not isinstance(job_wrapper, TaskWrapper):
            runner_name = "tasks"
        else:
            runner_name = ( job_wrapper.get_job_runner().split(":", 1) )[0]
        return runner_name

    def put( self, job_wrapper ):
        try:
            runner_name = self.__get_runner_name( job_wrapper )
            if self.app.config.use_tasked_jobs and job_wrapper.tool.parallelism is not None and isinstance(job_wrapper, TaskWrapper):
                #DBTODO Refactor
                log.debug( "dispatching task %s, of job %d, to %s runner" %( job_wrapper.task_id, job_wrapper.job_id, runner_name ) )
            else:
                log.debug( "dispatching job %d to %s runner" %( job_wrapper.job_id, runner_name ) )
            self.job_runners[runner_name].put( job_wrapper )
        except KeyError:
            log.error( 'put(): (%s) Invalid job runner: %s' % ( job_wrapper.job_id, runner_name ) )
            job_wrapper.fail( 'Unable to run job due to a misconfiguration of the Galaxy job running system.  Please contact a site administrator.' )

    def stop( self, job ):
        runner_name = ( job.job_runner_name.split(":", 1) )[0]
        log.debug( "stopping job %d in %s runner" %( job.id, runner_name ) )
        try:
            self.job_runners[runner_name].stop_job( job )
        except KeyError:
            log.error( 'stop(): (%s) Invalid job runner: %s' % ( job_wrapper.job_id, runner_name ) )
            # Job and output dataset states have already been updated, so nothing is done here.

    def recover( self, job, job_wrapper ):
        runner_name = ( job.job_runner_name.split(":", 1) )[0]
        log.debug( "recovering job %d in %s runner" %( job.id, runner_name ) )
        try:
            self.job_runners[runner_name].recover( job, job_wrapper )
        except KeyError:
            log.error( 'recover(): (%s) Invalid job runner: %s' % ( job_wrapper.job_id, runner_name ) )
            job_wrapper.fail( 'Unable to run job due to a misconfiguration of the Galaxy job running system.  Please contact a site administrator.' )

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

        self.track_jobs_in_database = app.config.get_bool( 'track_jobs_in_database', False )

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
        jobs_to_check = []
        if self.track_jobs_in_database:
            # Clear the session so we get fresh states for job and all datasets
            self.sa_session.expunge_all()
            # Fetch all new jobs
            newly_deleted_jobs = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                                     .filter( model.Job.state == model.Job.states.DELETED_NEW ).all()
            for job in newly_deleted_jobs:
                jobs_to_check.append( ( job, None ) )
        # Also pull from the queue (in the case of Administrative stopped jobs)
        try:
            while 1:
                message = self.queue.get_nowait()
                if message is self.STOP_SIGNAL:
                    return
                # Unpack the message
                job_id, error_msg = message
                # Get the job object and append to watch queue
                jobs_to_check.append( ( self.sa_session.query( model.Job ).get( job_id ), error_msg ) )
        except Empty:
            pass
        for job, error_msg in jobs_to_check:
            if error_msg is not None:
                job.state = job.states.ERROR
                job.info = error_msg
            else:
                job.state = job.states.DELETED
            self.sa_session.add( job )
            self.sa_session.flush()
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
            if not self.track_jobs_in_database:
                self.queue.put( self.STOP_SIGNAL )
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

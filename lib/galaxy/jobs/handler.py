"""
Galaxy job handler, prepares, runs, tracks, and finishes Galaxy jobs
"""

import os
import time
import logging
import threading
from Queue import Queue, Empty

from sqlalchemy.sql.expression import and_, or_, select, func

from galaxy import util, model
from galaxy.jobs import Sleeper, JobWrapper, TaskWrapper

log = logging.getLogger( __name__ )

# States for running a job. These are NOT the same as data states
JOB_WAIT, JOB_ERROR, JOB_INPUT_ERROR, JOB_INPUT_DELETED, JOB_READY, JOB_DELETED, JOB_ADMIN_DELETED, JOB_USER_OVER_QUOTA = 'wait', 'error', 'input_error', 'input_deleted', 'ready', 'deleted', 'admin_deleted', 'user_over_quota'
DEFAULT_JOB_PUT_FAILURE_MESSAGE = 'Unable to run job due to a misconfiguration of the Galaxy job running system.  Please contact a site administrator.'

class JobHandler( object ):
    """
    Handle the preparation, running, tracking, and finishing of jobs
    """
    def __init__( self, app ):
        self.app = app
        # The dispatcher launches the underlying job runners
        self.dispatcher = DefaultJobDispatcher( app )
        # Queues for starting and stopping jobs
        self.job_queue = JobHandlerQueue( app, self.dispatcher )
        self.job_stop_queue = JobHandlerStopQueue( app, self.dispatcher )
    def start( self ):
        self.job_queue.start()
    def shutdown( self ):
        self.job_queue.shutdown()
        self.job_stop_queue.shutdown()

class JobHandlerQueue( object ):
    """
    Job manager, waits for jobs to be runnable and then dispatches to
    a JobRunner.
    """
    STOP_SIGNAL = object()

    def __init__( self, app, dispatcher ):
        """Start the job manager"""
        self.app = app
        self.dispatcher = dispatcher

        self.sa_session = app.model.context
        self.track_jobs_in_database = self.app.config.track_jobs_in_database

        # Keep track of the pid that started the job manager, only it
        # has valid threads
        self.parent_pid = os.getpid()
        # Contains new jobs. Note this is not used if track_jobs_in_database is True
        self.queue = Queue()
        # Contains jobs that are waiting (only use from monitor thread)
        self.waiting_jobs = []
        # Helper for interruptable sleep
        self.sleeper = Sleeper()
        self.running = True
        self.monitor_thread = threading.Thread( name="JobHandlerQueue.monitor_thread", target=self.__monitor )
        self.monitor_thread.setDaemon( True )

    def start( self ):
        """
        The JobManager should start, and then start its Handler, if it has one.
        """
        # Recover jobs at startup
        self.__check_jobs_at_startup()
        # Start the queue
        self.monitor_thread.start()
        log.info( "job handler queue started" )

    def __check_jobs_at_startup( self ):
        """
        Checks all jobs that are in the 'new', 'queued' or 'running' state in
        the database and requeues or cleans up as necessary.  Only run as the
        job manager starts.
        """
        for job in self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                                  .filter( ( ( model.Job.state == model.Job.states.NEW ) \
                                             | ( model.Job.state == model.Job.states.RUNNING ) \
                                             | ( model.Job.state == model.Job.states.QUEUED ) ) \
                                           & ( model.Job.handler == self.app.config.server_name ) ):
            if job.tool_id not in self.app.toolbox.tools_by_id:
                log.warning( "(%s) Tool '%s' removed from tool config, unable to recover job" % ( job.id, job.tool_id ) )
                JobWrapper( job, self ).fail( 'This tool was disabled before the job completed.  Please contact your Galaxy administrator.' )
            elif job.job_runner_name is None or (job.job_runner_name is not None and job.job_runner_external_id is None):
                if job.job_runner_name is None:
                    log.debug( "(%s) No job runner assigned and job still in '%s' state, adding to the job handler queue" % ( job.id, job.state ) )
                else:
                    log.debug( "(%s) Job runner assigned but no external ID recorded, adding to the job handler queue" % job.id )
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
            hda_not_ready = self.sa_session.query(model.Job.id).enable_eagerloads(False) \
                    .join(model.JobToInputDatasetAssociation) \
                    .join(model.HistoryDatasetAssociation) \
                    .join(model.Dataset) \
                    .filter(and_((model.Job.state == model.Job.states.NEW),
                                 or_((model.HistoryDatasetAssociation._state == model.HistoryDatasetAssociation.states.FAILED_METADATA),
                                     (model.HistoryDatasetAssociation.deleted == True ),
                                     (model.Dataset.state != model.Dataset.states.OK ),
                                     (model.Dataset.deleted == True)))).subquery()
            ldda_not_ready = self.sa_session.query(model.Job.id).enable_eagerloads(False) \
                    .join(model.JobToInputLibraryDatasetAssociation) \
                    .join(model.LibraryDatasetDatasetAssociation) \
                    .join(model.Dataset) \
                    .filter(and_((model.Job.state == model.Job.states.NEW),
                                 or_((model.LibraryDatasetDatasetAssociation._state != None),
                                     (model.LibraryDatasetDatasetAssociation.deleted == True),
                                     (model.Dataset.state != model.Dataset.states.OK),
                                     (model.Dataset.deleted == True)))).subquery()
            jobs_to_check = self.sa_session.query(model.Job).enable_eagerloads(False) \
                    .filter(and_((model.Job.state == model.Job.states.NEW),
                                 (model.Job.handler == self.app.config.server_name),
                                 ~model.Job.table.c.id.in_(hda_not_ready),
                                 ~model.Job.table.c.id.in_(ldda_not_ready))) \
                    .order_by(model.Job.id).all()
            # Ensure that we get new job counts on each iteration
            self.__clear_user_job_count()
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
                # Check the job's dependencies, requeue if they're not done.
                # Some of these states will only happen when using the in-memory job queue
                job_state = self.__check_if_ready_to_run( job )
                if job_state == JOB_WAIT:
                    if not self.track_jobs_in_database:
                        new_waiting_jobs.append( job.id )
                elif job_state == JOB_INPUT_ERROR:
                    log.info( "(%d) Job unable to run: one or more inputs in error state" % job.id )
                elif job_state == JOB_INPUT_DELETED:
                    log.info( "(%d) Job unable to run: one or more inputs deleted" % job.id )
                elif job_state == JOB_READY:
                    self.dispatcher.put( JobWrapper( job, self ) )
                    log.info( "(%d) Job dispatched" % job.id )
                elif job_state == JOB_DELETED:
                    log.info( "(%d) Job deleted by user while still queued" % job.id )
                elif job_state == JOB_ADMIN_DELETED:
                    log.info( "(%d) Job deleted by admin while still queued" % job.id )
                elif job_state == JOB_USER_OVER_QUOTA:
                    log.info( "(%d) User (%s) is over quota: job paused" % ( job.id, job.user_id ) )
                    job.state = model.Job.states.PAUSED
                    for dataset_assoc in job.output_datasets + job.output_library_datasets:
                        dataset_assoc.dataset.dataset.state = model.Dataset.states.PAUSED
                        dataset_assoc.dataset.info = "Execution of this dataset's job is paused because you were over your disk quota at the time it was ready to run"
                        self.sa_session.add( dataset_assoc.dataset.dataset )
                    self.sa_session.add( job )
                else:
                    log.error( "(%d) Job in unknown state '%s'" % ( job.id, job_state ) )
                    if not self.track_jobs_in_database:
                        new_waiting_jobs.append( job.id )
            except Exception:
                log.exception( "failure running job %d" % job.id )
        # Update the waiting list
        self.waiting_jobs = new_waiting_jobs
        # Flush, if we updated the state
        self.sa_session.flush()
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
        # If tracking in the database, job.state is guaranteed to be NEW and the inputs are guaranteed to be OK
        if not self.track_jobs_in_database:
            if job.state == model.Job.states.DELETED:
                return JOB_DELETED
            elif job.state == model.Job.states.ERROR:
                return JOB_ADMIN_DELETED
            for dataset_assoc in job.input_datasets + job.input_library_datasets:
                idata = dataset_assoc.dataset
                if not idata:
                    continue
                # don't run jobs for which the input dataset was deleted
                if idata.deleted:
                    JobWrapper( job, self ).fail( "input data %s (file: %s) was deleted before the job started" % ( idata.hid, idata.file_name ) )
                    return JOB_INPUT_DELETED
                # an error in the input data causes us to bail immediately
                elif idata.state == idata.states.ERROR:
                    JobWrapper( job, self ).fail( "input data %s is in error state" % ( idata.hid ) )
                    return JOB_INPUT_ERROR
                elif idata.state == idata.states.FAILED_METADATA:
                    JobWrapper( job, self ).fail( "input data %s failed to properly set metadata" % ( idata.hid ) )
                    return JOB_INPUT_ERROR
                elif idata.state != idata.states.OK and not ( idata.state == idata.states.SETTING_METADATA and job.tool_id is not None and job.tool_id == self.app.datatypes_registry.set_external_metadata_tool.id ):
                    # need to requeue
                    return JOB_WAIT
        state = self.__check_user_jobs( job )
        if state == JOB_READY and self.app.config.enable_quotas:
            quota = self.app.quota_agent.get_quota( job.user )
            if quota is not None:
                try:
                    usage = self.app.quota_agent.get_usage( user=job.user, history=job.history )
                    if usage > quota:
                        return JOB_USER_OVER_QUOTA
                except AssertionError, e:
                    pass # No history, should not happen with an anon user
        return state

    def __clear_user_job_count( self ):
        self.user_job_count = {}
        self.user_job_count_per_runner = {}

    def __check_user_jobs( self, job ):
        if job.user:
            # Check the hard limit first
            if self.app.config.registered_user_job_limit:
                # Cache the job count if necessary
                if not self.user_job_count:
                    query = self.sa_session.execute(select([model.Job.table.c.user_id, func.count(model.Job.table.c.user_id)]) \
                            .where(and_(model.Job.table.c.state.in_((model.Job.states.QUEUED, model.Job.states.RUNNING)), (model.Job.table.c.user_id is not None))) \
                            .group_by(model.Job.table.c.user_id))
                    for row in query:
                        self.user_job_count[row[0]] = row[1]
                if self.user_job_count.get(job.user_id, 0) >= self.app.config.registered_user_job_limit:
                    return JOB_WAIT
            # If we pass the hard limit, also check the per-runner count
            if job.job_runner_name in self.app.config.job_limits:
                # Cache the job count if necessary
                if job.job_runner_name not in self.user_job_count_per_runner:
                    self.user_job_count_per_runner[job.job_runner_name] = {}
                    query_url, limit = self.app.config.job_limits[job.job_runner_name]
                    base_query = select([model.Job.table.c.user_id, model.Job.table.c.job_runner_name, func.count(model.Job.table.c.user_id).label('job_count')]) \
                                .where(model.Job.table.c.state.in_((model.Job.states.QUEUED, model.Job.states.RUNNING))) \
                                .group_by(model.Job.table.c.user_id, model.Job.table.c.job_runner_name)
                    if '%' in query_url or '_' in query_url:
                        subq = base_query.having(model.Job.table.c.job_runner_name.like(query_url)).alias('subq')
                        query = self.sa_session.execute(select([subq.c.user_id, func.sum(subq.c.job_count).label('job_count')]).group_by(subq.c.user_id))
                    else:
                        query = self.sa_session.execute(base_query.having(model.Job.table.c.job_runner_name == query_url))
                    for row in query:
                        self.user_job_count_per_runner[job.job_runner_name][row['user_id']] = row['job_count']
                if self.user_job_count_per_runner[job.job_runner_name].get(job.user_id, 0) >= self.app.config.job_limits[job.job_runner_name][1]:
                    return JOB_WAIT
        elif job.galaxy_session:
            # Anonymous users only get the hard limit
            if self.app.config.anonymous_user_job_limit:
                count = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                            .filter( and_( model.Job.session_id == job.galaxy_session.id,
                                           or_( model.Job.state == model.Job.states.RUNNING,
                                                model.Job.state == model.Job.states.QUEUED ) ) ).count()
                if count >= self.app.config.anonymous_user_job_limit:
                    return JOB_WAIT
        else:
            log.warning( 'Job %s is not associated with a user or session so job concurrency limit cannot be checked.' % job.id )
        return JOB_READY

    def put( self, job_id, tool_id ):
        """Add a job to the queue (by job identifier)"""
        if not self.track_jobs_in_database:
            self.queue.put( ( job_id, tool_id ) )
            self.sleeper.wake()

    def shutdown( self ):
        """Attempts to gracefully shut down the worker thread"""
        if self.parent_pid != os.getpid():
            # We're not the real job queue, do nothing
            return
        else:
            log.info( "sending stop signal to worker thread" )
            self.running = False
            if not self.app.config.track_jobs_in_database:
                self.queue.put( self.STOP_SIGNAL )
            self.sleeper.wake()
            log.info( "job handler queue stopped" )
            self.dispatcher.shutdown()

class JobHandlerStopQueue( object ):
    """
    A queue for jobs which need to be terminated prematurely.
    """
    STOP_SIGNAL = object()
    def __init__( self, app, dispatcher ):
        self.app = app
        self.dispatcher = dispatcher

        self.sa_session = app.model.context

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
        self.monitor_thread = threading.Thread( name="JobHandlerStopQueue.monitor_thread", target=self.monitor )
        self.monitor_thread.setDaemon( True )
        self.monitor_thread.start()
        log.info( "job handler stop queue started" )

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
        if self.app.config.track_jobs_in_database:
            # Clear the session so we get fresh states for job and all datasets
            self.sa_session.expunge_all()
            # Fetch all new jobs
            newly_deleted_jobs = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                                     .filter( ( model.Job.state == model.Job.states.DELETED_NEW ) \
                                              & ( model.Job.handler == self.app.config.server_name ) ).all()
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
            if not self.app.config.track_jobs_in_database:
                self.queue.put( self.STOP_SIGNAL )
            self.sleeper.wake()
            log.info( "job handler stop queue stopped" )

class DefaultJobDispatcher( object ):
    def __init__( self, app ):
        self.app = app
        self.job_runners = {}
        start_job_runners = ["local", "lwr"]
        if app.config.start_job_runners is not None:
            start_job_runners.extend( [ x.strip() for x in util.listify( app.config.start_job_runners ) ] )
        if app.config.use_tasked_jobs:
            start_job_runners.append("tasks")
        for name in start_job_runners:
            self._load_plugin( name )
        log.debug( "Job runners: " + ':'.join( start_job_runners ) )

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
        if job_wrapper.can_split():
            runner_name = "tasks"
        else:
            runner_name = ( job_wrapper.get_job_runner_url().split(":", 1) )[0]
        return runner_name

    def put( self, job_wrapper ):
        try:
            runner_name = self.__get_runner_name( job_wrapper )
        except Exception, e:
            failure_message = getattr(e, 'failure_message', DEFAULT_JOB_PUT_FAILURE_MESSAGE )
            if failure_message == DEFAULT_JOB_PUT_FAILURE_MESSAGE:
                log.exception( 'Failed to generate job runner name' )
            else:
                log.debug( "Intentionally failing job with message (%s)" % failure_message )
            job_wrapper.fail( failure_message )
            return
        try:
            if isinstance(job_wrapper, TaskWrapper):
                #DBTODO Refactor
                log.debug( "dispatching task %s, of job %d, to %s runner" %( job_wrapper.task_id, job_wrapper.job_id, runner_name ) )
            else:
                log.debug( "dispatching job %d to %s runner" %( job_wrapper.job_id, runner_name ) )
            self.job_runners[runner_name].put( job_wrapper )
        except KeyError:
            log.error( 'put(): (%s) Invalid job runner: %s' % ( job_wrapper.job_id, runner_name ) )
            job_wrapper.fail( DEFAULT_JOB_PUT_FAILURE_MESSAGE )

    def stop( self, job ):
        """
        Stop the given job. The input variable job may be either a Job or a Task.
        """
        # The Job and Task classes have been modified so that their accessors
        # will return the appropriate value. 
        # Note that Jobs and Tasks have runner_names, which are distinct from
        # the job_runner_name and task_runner_name.

        if ( isinstance( job, model.Job ) ):
            log.debug( "Stopping job %d:", job.get_id() )
        elif( isinstance( job, model.Task ) ):
            log.debug( "Stopping job %d, task %d" 
                     % ( job.get_job().get_id(), job.get_id() ) )
        else:
            log.debug( "Unknown job to stop" )

        # The runner name is not set until the job has started.
        # If we're stopping a task, then the runner_name may be
        # None, in which case it hasn't been scheduled.
        if ( None != job.get_job_runner_name() ):
            runner_name = (job.get_job_runner_name().split(":",1))[0]
            if ( isinstance( job, model.Job ) ):
                log.debug( "stopping job %d in %s runner" %( job.get_id(), runner_name ) )
            elif ( isinstance( job, model.Task ) ):
                log.debug( "Stopping job %d, task %d in %s runner" 
                         % ( job.get_job().get_id(), job.get_id(), runner_name ) )
            try:
                self.job_runners[runner_name].stop_job( job )
            except KeyError:
                log.error( 'stop(): (%s) Invalid job runner: %s' % ( job_wrapper.job_id, runner_name ) )
                # Job and output dataset states have already been updated, so nothing is done here.

    def recover( self, job, job_wrapper ):
        runner_name = ( job.job_runner_name.split(":", 1) )[0]
        log.debug( "recovering job %d in %s runner" %( job.get_id(), runner_name ) )
        try:
            self.job_runners[runner_name].recover( job, job_wrapper )
        except KeyError:
            log.error( 'recover(): (%s) Invalid job runner: %s' % ( job_wrapper.job_id, runner_name ) )
            job_wrapper.fail( DEFAULT_JOB_PUT_FAILURE_MESSAGE )

    def shutdown( self ):
        for runner in self.job_runners.itervalues():
            runner.shutdown()

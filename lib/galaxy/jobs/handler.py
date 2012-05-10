"""
Galaxy job handler, prepares, runs, tracks, and finishes Galaxy jobs
"""

import os
import time
import logging
import threading
from Queue import Queue, Empty

from sqlalchemy.sql.expression import and_, or_

from galaxy import util, model
from galaxy.jobs import Sleeper, JobWrapper, TaskWrapper

log = logging.getLogger( __name__ )

# States for running a job. These are NOT the same as data states
JOB_WAIT, JOB_ERROR, JOB_INPUT_ERROR, JOB_INPUT_DELETED, JOB_READY, JOB_DELETED, JOB_ADMIN_DELETED = 'wait', 'error', 'input_error', 'input_deleted', 'ready', 'deleted', 'admin_deleted'

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
        ## This and jobs_to_check[] are closest to a "Job Queue"
        self.waiting_jobs = []
        # Helper for interruptable sleep
        self.sleeper = Sleeper()
        self.running = True
        self.monitor_thread = threading.Thread( target=self.__monitor )

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
            elif job.job_runner_name is None:
                log.debug( "(%s) No job runner assigned and job still in '%s' state, adding to the job handler queue" % ( job.id, job.state ) )
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
            jobs_to_check = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                                .filter( ( model.Job.state == model.Job.states.NEW ) \
                                         & ( model.Job.handler == self.app.config.server_name ) ).all()
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
                else:
                    log.error( "(%d) Job in unknown state '%s'" % ( job.id, job_state ) )
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
        self.monitor_thread = threading.Thread( target=self.monitor )
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
        start_job_runners = ["local"]
        if app.config.start_job_runners is not None:
            start_job_runners.extend( [ x.strip() for x in util.listify( app.config.start_job_runners ) ] )
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

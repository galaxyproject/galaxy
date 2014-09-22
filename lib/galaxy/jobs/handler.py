"""
Galaxy job handler, prepares, runs, tracks, and finishes Galaxy jobs
"""

import os
import time
import logging
import threading
from Queue import Queue, Empty

from sqlalchemy.sql.expression import and_, or_, select, func

from galaxy import model
from galaxy.util.sleeper import Sleeper
from galaxy.jobs import JobWrapper, TaskWrapper, JobDestination
from galaxy.jobs.mapper import JobNotReadyException

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
        self.job_lock = False

        self.sa_session = app.model.context
        self.track_jobs_in_database = self.app.config.track_jobs_in_database

        # Initialize structures for handling job limits
        self.__clear_job_count()

        # Keep track of the pid that started the job manager, only it
        # has valid threads
        self.parent_pid = os.getpid()
        # Contains new jobs. Note this is not used if track_jobs_in_database is True
        self.queue = Queue()
        # Contains jobs that are waiting (only use from monitor thread)
        self.waiting_jobs = []
        # Contains wrappers of jobs that are limited or ready (so they aren't created unnecessarily/multiple times)
        self.job_wrappers = {}
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

    def job_wrapper( self, job, use_persisted_destination=False ):
        return JobWrapper( job, self, use_persisted_destination=use_persisted_destination )

    def job_pair_for_id( self, id ):
        job = self.sa_session.query( model.Job ).get( id )
        return job, self.job_wrapper( job, use_persisted_destination=True )

    def __check_jobs_at_startup( self ):
        """
        Checks all jobs that are in the 'new', 'queued' or 'running' state in
        the database and requeues or cleans up as necessary.  Only run as the
        job handler starts.
        In case the activation is enforced it will filter out the jobs of inactive users.
        """
        jobs_at_startup = []
        if self.track_jobs_in_database:
            in_list = ( model.Job.states.QUEUED,
                        model.Job.states.RUNNING )
        else:
            in_list = ( model.Job.states.NEW,
                        model.Job.states.QUEUED,
                        model.Job.states.RUNNING )
        if self.app.config.user_activation_on:
                jobs_at_startup = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                                  .outerjoin( model.User ) \
                                  .filter( model.Job.state.in_( in_list ) \
                                           & ( model.Job.handler == self.app.config.server_name ) \
                                           & or_( ( model.Job.user_id == None ), ( model.User.active == True ) ) ).all()
        else:
            jobs_at_startup = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                              .filter( model.Job.state.in_( in_list ) \
                                       & ( model.Job.handler == self.app.config.server_name ) ).all()

        for job in jobs_at_startup:
            if job.tool_id not in self.app.toolbox.tools_by_id:
                log.warning( "(%s) Tool '%s' removed from tool config, unable to recover job" % ( job.id, job.tool_id ) )
                self.job_wrapper( job ).fail( 'This tool was disabled before the job completed.  Please contact your Galaxy administrator.' )
            elif job.job_runner_name is not None and job.job_runner_external_id is None:
                # This could happen during certain revisions of Galaxy where a runner URL was persisted before the job was dispatched to a runner.
                log.debug( "(%s) Job runner assigned but no external ID recorded, adding to the job handler queue" % job.id )
                job.job_runner_name = None
                if self.track_jobs_in_database:
                    job.state = model.Job.states.NEW
                else:
                    self.queue.put( ( job.id, job.tool_id ) )
            elif job.job_runner_name is not None and job.job_runner_external_id is not None and job.destination_id is None:
                # This is the first start after upgrading from URLs to destinations, convert the URL to a destination and persist
                job_wrapper = self.job_wrapper( job )
                job_destination = self.dispatcher.url_to_destination(job.job_runner_name)
                if job_destination.id is None:
                    job_destination.id = 'legacy_url'
                job_wrapper.set_job_destination(job_destination, job.job_runner_external_id)
                self.dispatcher.recover( job, job_wrapper )
                log.info('(%s) Converted job from a URL to a destination and recovered' % (job.id))
            elif job.job_runner_name is None:
                # Never (fully) dispatched
                log.debug( "(%s) No job runner assigned and job still in '%s' state, adding to the job handler queue" % ( job.id, job.state ) )
                if self.track_jobs_in_database:
                    job.state = model.Job.states.NEW
                else:
                    self.queue.put( ( job.id, job.tool_id ) )
            else:
                # Already dispatched and running
                job_wrapper = self.job_wrapper( job )
                # Use the persisted destination as its params may differ from
                # what's in the job_conf xml
                job_destination = JobDestination(id=job.destination_id, runner=job.job_runner_name, params=job.destination_params)
                # resubmits are not persisted (it's a good thing) so they
                # should be added back to the in-memory destination on startup
                try:
                    config_job_destination = self.app.job_config.get_destination( job.destination_id )
                    job_destination.resubmit = config_job_destination.resubmit
                except KeyError:
                    log.warning( '(%s) Recovered destination id (%s) does not exist in job config (but this may be normal in the case of a dynamically generated destination)', job.id, job.destination_id )
                job_wrapper.job_runner_mapper.cached_job_destination = job_destination
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
                # If jobs are locked, there's nothing to monitor and we skip
                # to the sleep.
                if not self.job_lock:
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
        it is marked as having errors and removed from the queue. If the job
        belongs to an inactive user it is ignored.
        Otherwise, the job is dispatched.
        """
        # Pull all new jobs from the queue at once
        jobs_to_check = []
        resubmit_jobs = []
        if self.track_jobs_in_database:
            # Clear the session so we get fresh states for job and all datasets
            self.sa_session.expunge_all()
            # Fetch all new jobs
            hda_not_ready = self.sa_session.query(model.Job.id).enable_eagerloads(False) \
                    .join(model.JobToInputDatasetAssociation) \
                    .join(model.HistoryDatasetAssociation) \
                    .join(model.Dataset) \
                    .filter(and_( (model.Job.state == model.Job.states.NEW ),
                                 or_( ( model.HistoryDatasetAssociation._state == model.HistoryDatasetAssociation.states.FAILED_METADATA ),
                                      ( model.HistoryDatasetAssociation.deleted == True ),
                                      ( model.Dataset.state != model.Dataset.states.OK ),
                                      ( model.Dataset.deleted == True) ) ) ).subquery()
            ldda_not_ready = self.sa_session.query(model.Job.id).enable_eagerloads(False) \
                    .join(model.JobToInputLibraryDatasetAssociation) \
                    .join(model.LibraryDatasetDatasetAssociation) \
                    .join(model.Dataset) \
                    .filter(and_((model.Job.state == model.Job.states.NEW),
                                 or_((model.LibraryDatasetDatasetAssociation._state != None),
                                     (model.LibraryDatasetDatasetAssociation.deleted == True),
                                     (model.Dataset.state != model.Dataset.states.OK),
                                     (model.Dataset.deleted == True)))).subquery()
            if self.app.config.user_activation_on:
                jobs_to_check = self.sa_session.query(model.Job).enable_eagerloads(False) \
                        .outerjoin( model.User ) \
                        .filter(and_((model.Job.state == model.Job.states.NEW),
                                    or_((model.Job.user_id == None), (model.User.active == True)),
                                     (model.Job.handler == self.app.config.server_name),
                                     ~model.Job.table.c.id.in_(hda_not_ready),
                                     ~model.Job.table.c.id.in_(ldda_not_ready))) \
                        .order_by(model.Job.id).all()
            else:
                jobs_to_check = self.sa_session.query(model.Job).enable_eagerloads(False) \
                    .filter(and_((model.Job.state == model.Job.states.NEW),
                                 (model.Job.handler == self.app.config.server_name),
                                 ~model.Job.table.c.id.in_(hda_not_ready),
                                 ~model.Job.table.c.id.in_(ldda_not_ready))) \
                    .order_by(model.Job.id).all()
            # Fetch all "resubmit" jobs
            resubmit_jobs = self.sa_session.query(model.Job).enable_eagerloads(False) \
                    .filter(and_((model.Job.state == model.Job.states.RESUBMITTED),
                                (model.Job.handler == self.app.config.server_name))) \
                    .order_by(model.Job.id).all()
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
        # Ensure that we get new job counts on each iteration
        self.__clear_job_count()
        # Check resubmit jobs first so that limits of new jobs will still be enforced
        for job in resubmit_jobs:
            log.debug( '(%s) Job was resubmitted and is being dispatched immediately', job.id )
            # Reassemble resubmit job destination from persisted value
            jw = self.job_wrapper( job )
            jw.job_runner_mapper.cached_job_destination = JobDestination( id=job.destination_id, runner=job.job_runner_name, params=job.destination_params )
            self.increase_running_job_count(job.user_id, jw.job_destination.id)
            self.dispatcher.put( jw )
        # Iterate over new and waiting jobs and look for any that are
        # ready to run
        new_waiting_jobs = []
        for job in jobs_to_check:
            try:
                # Check the job's dependencies, requeue if they're not done.
                # Some of these states will only happen when using the in-memory job queue
                job_state = self.__check_job_state( job )
                if job_state == JOB_WAIT:
                    new_waiting_jobs.append( job.id )
                elif job_state == JOB_INPUT_ERROR:
                    log.info( "(%d) Job unable to run: one or more inputs in error state" % job.id )
                elif job_state == JOB_INPUT_DELETED:
                    log.info( "(%d) Job unable to run: one or more inputs deleted" % job.id )
                elif job_state == JOB_READY:
                    self.dispatcher.put( self.job_wrappers.pop( job.id ) )
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
                elif job_state == JOB_ERROR:
                    log.error( "(%d) Error checking job readiness" % job.id )
                else:
                    log.error( "(%d) Job in unknown state '%s'" % ( job.id, job_state ) )
                    new_waiting_jobs.append( job.id )
            except Exception:
                log.exception( "failure running job %d" % job.id )
        # Update the waiting list
        if not self.track_jobs_in_database:
            self.waiting_jobs = new_waiting_jobs
        # Remove cached wrappers for any jobs that are no longer being tracked
        for id in self.job_wrappers.keys():
            if id not in new_waiting_jobs:
                del self.job_wrappers[id]
        # Flush, if we updated the state
        self.sa_session.flush()
        # Done with the session
        self.sa_session.remove()

    def __check_job_state( self, job ):
        """
        Check if a job is ready to run by verifying that each of its input
        datasets is ready (specifically in the OK state). If any input dataset
        has an error, fail the job and return JOB_INPUT_ERROR. If any input
        dataset is deleted, fail the job and return JOB_INPUT_DELETED.  If all
        input datasets are in OK state, return JOB_READY indicating that the
        job can be dispatched. Otherwise, return JOB_WAIT indicating that input
        datasets are still being prepared.
        """
        if not self.track_jobs_in_database:
            in_memory_not_ready_state = self.__verify_in_memory_job_inputs( job )
            if in_memory_not_ready_state:
                return in_memory_not_ready_state

        # Else, if tracking in the database, job.state is guaranteed to be NEW and
        # the inputs are guaranteed to be OK.

        # Create the job wrapper so that the destination can be set
        job_id = job.id
        job_wrapper = self.job_wrappers.get( job_id, None )
        if not job_wrapper:
            job_wrapper = self.job_wrapper( job )
            self.job_wrappers[ job_id ] = job_wrapper

        # If state == JOB_READY, assume job_destination also set - otherwise
        # in case of various error or cancelled states do not assume
        # destination has been set.
        state, job_destination = self.__verify_job_ready( job, job_wrapper )

        if state == JOB_READY:
            # PASS.  increase usage by one job (if caching) so that multiple jobs aren't dispatched on this queue iteration
            self.increase_running_job_count(job.user_id, job_destination.id )
        return state

    def __verify_job_ready( self, job, job_wrapper ):
        """ Compute job destination and verify job is ready at that
        destination by checking job limits and quota. If this method
        return a job state of JOB_READY - it MUST also return a job
        destination.
        """
        job_destination = None
        try:
            assert job_wrapper.tool is not None, 'This tool was disabled before the job completed.  Please contact your Galaxy administrator.'
            # Cause the job_destination to be set and cached by the mapper
            job_destination = job_wrapper.job_destination
        except AssertionError as e:
            log.warning( "(%s) Tool '%s' removed from tool config, unable to run job" % ( job.id, job.tool_id ) )
            job_wrapper.fail( e )
            return JOB_ERROR, job_destination
        except JobNotReadyException as e:
            job_state = e.job_state or JOB_WAIT
            return job_state, None
        except Exception, e:
            failure_message = getattr( e, 'failure_message', DEFAULT_JOB_PUT_FAILURE_MESSAGE )
            if failure_message == DEFAULT_JOB_PUT_FAILURE_MESSAGE:
                log.exception( 'Failed to generate job destination' )
            else:
                log.debug( "Intentionally failing job with message (%s)" % failure_message )
            job_wrapper.fail( failure_message )
            return JOB_ERROR, job_destination
        # job is ready to run, check limits
        # TODO: these checks should be refactored to minimize duplication and made more modular/pluggable
        state = self.__check_destination_jobs( job, job_wrapper )
        if state == JOB_READY:
            state = self.__check_user_jobs( job, job_wrapper )
        if state == JOB_READY and self.app.config.enable_quotas:
            quota = self.app.quota_agent.get_quota( job.user )
            if quota is not None:
                try:
                    usage = self.app.quota_agent.get_usage( user=job.user, history=job.history )
                    if usage > quota:
                        return JOB_USER_OVER_QUOTA, job_destination
                except AssertionError, e:
                    pass  # No history, should not happen with an anon user
        return state, job_destination

    def __verify_in_memory_job_inputs( self, job ):
        """ Perform the same checks that happen via SQL for in-memory managed
        jobs.
        """
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
                self.job_wrappers.pop(job.id, self.job_wrapper( job )).fail( "input data %s (file: %s) was deleted before the job started" % ( idata.hid, idata.file_name ) )
                return JOB_INPUT_DELETED
            # an error in the input data causes us to bail immediately
            elif idata.state == idata.states.ERROR:
                self.job_wrappers.pop(job.id, self.job_wrapper( job )).fail( "input data %s is in error state" % ( idata.hid ) )
                return JOB_INPUT_ERROR
            elif idata.state == idata.states.FAILED_METADATA:
                self.job_wrappers.pop(job.id, self.job_wrapper( job )).fail( "input data %s failed to properly set metadata" % ( idata.hid ) )
                return JOB_INPUT_ERROR
            elif idata.state != idata.states.OK and not ( idata.state == idata.states.SETTING_METADATA and job.tool_id is not None and job.tool_id == self.app.datatypes_registry.set_external_metadata_tool.id ):
                # need to requeue
                return JOB_WAIT

        # All inputs ready to go.
        return None

    def __clear_job_count( self ):
        self.user_job_count = None
        self.user_job_count_per_destination = None
        self.total_job_count_per_destination = None

    def get_user_job_count(self, user_id):
        self.__cache_user_job_count()
        # This could have been incremented by a previous job dispatched on this iteration, even if we're not caching
        rval = self.user_job_count.get(user_id, 0)
        if not self.app.config.cache_user_job_count:
            result = self.sa_session.execute(select([func.count(model.Job.table.c.id)]) \
                .where(and_(model.Job.table.c.state.in_((model.Job.states.QUEUED,
                                                         model.Job.states.RUNNING,
                                                         model.Job.states.RESUBMITTED)),
                            (model.Job.table.c.user_id == user_id))))
            for row in result:
                # there should only be one row
                rval += row[0]
        return rval

    def __cache_user_job_count( self ):
        # Cache the job count if necessary
        if self.user_job_count is None and self.app.config.cache_user_job_count:
            self.user_job_count = {}
            query = self.sa_session.execute(select([model.Job.table.c.user_id, func.count(model.Job.table.c.user_id)]) \
                .where(and_(model.Job.table.c.state.in_((model.Job.states.QUEUED,
                                                         model.Job.states.RUNNING,
                                                         model.Job.states.RESUBMITTED)),
                            (model.Job.table.c.user_id is not None))) \
                                .group_by(model.Job.table.c.user_id))
            for row in query:
                self.user_job_count[row[0]] = row[1]
        elif self.user_job_count is None:
            self.user_job_count = {}

    def get_user_job_count_per_destination(self, user_id):
        self.__cache_user_job_count_per_destination()
        cached = self.user_job_count_per_destination.get(user_id, {})
        if self.app.config.cache_user_job_count:
            rval = cached
        else:
            # The cached count is still used even when we're not caching, it is
            # incremented when a job is run by this handler to ensure that
            # multiple jobs can't get past the limits in one iteration of the
            # queue.
            rval = {}
            rval.update(cached)
            result = self.sa_session.execute(select([model.Job.table.c.destination_id, func.count(model.Job.table.c.destination_id).label('job_count')]) \
                                            .where(and_(model.Job.table.c.state.in_((model.Job.states.QUEUED, model.Job.states.RUNNING)), (model.Job.table.c.user_id == user_id))) \
                                            .group_by(model.Job.table.c.destination_id))
            for row in result:
                # Add the count from the database to the cached count
                rval[row['destination_id']] = rval.get(row['destination_id'], 0) + row['job_count']
        return rval

    def __cache_user_job_count_per_destination(self):
        # Cache the job count if necessary
        if self.user_job_count_per_destination is None and self.app.config.cache_user_job_count:
            self.user_job_count_per_destination = {}
            result = self.sa_session.execute(select([model.Job.table.c.user_id, model.Job.table.c.destination_id, func.count(model.Job.table.c.user_id).label('job_count')]) \
                                            .where(and_(model.Job.table.c.state.in_((model.Job.states.QUEUED, model.Job.states.RUNNING)))) \
                                            .group_by(model.Job.table.c.user_id, model.Job.table.c.destination_id))
            for row in result:
                if row['user_id'] not in self.user_job_count_per_destination:
                    self.user_job_count_per_destination[row['user_id']] = {}
                self.user_job_count_per_destination[row['user_id']][row['destination_id']] = row['job_count']
        elif self.user_job_count_per_destination is None:
            self.user_job_count_per_destination = {}

    def increase_running_job_count(self, user_id, destination_id):
        if self.app.job_config.limits.registered_user_concurrent_jobs or \
           self.app.job_config.limits.anonymous_user_concurrent_jobs or \
           self.app.job_config.limits.destination_user_concurrent_jobs:
            if self.user_job_count is None:
                self.user_job_count = {}
            if self.user_job_count_per_destination is None:
                self.user_job_count_per_destination = {}
            self.user_job_count[user_id] = self.user_job_count.get(user_id, 0) + 1
            if user_id not in self.user_job_count_per_destination:
                self.user_job_count_per_destination[user_id] = {}
            self.user_job_count_per_destination[user_id][destination_id] = self.user_job_count_per_destination[user_id].get(destination_id, 0) + 1
        if self.app.job_config.limits.destination_total_concurrent_jobs:
            if self.total_job_count_per_destination is None:
                self.total_job_count_per_destination = {}
            self.total_job_count_per_destination[destination_id] = self.total_job_count_per_destination.get(destination_id, 0) + 1

    def __check_user_jobs( self, job, job_wrapper ):
        # TODO: Update output datasets' _state = LIMITED or some such new
        # state, so the UI can reflect what jobs are waiting due to concurrency
        # limits
        if job.user:
            # Check the hard limit first
            if self.app.job_config.limits.registered_user_concurrent_jobs:
                count = self.get_user_job_count(job.user_id)
                # Check the user's number of dispatched jobs against the overall limit
                if count >= self.app.job_config.limits.registered_user_concurrent_jobs:
                    return JOB_WAIT
            # If we pass the hard limit, also check the per-destination count
            id = job_wrapper.job_destination.id
            count_per_id = self.get_user_job_count_per_destination(job.user_id)
            if id in self.app.job_config.limits.destination_user_concurrent_jobs:
                count = count_per_id.get(id, 0)
                # Check the user's number of dispatched jobs in the assigned destination id against the limit for that id
                if count >= self.app.job_config.limits.destination_user_concurrent_jobs[id]:
                    return JOB_WAIT
            # If we pass the destination limit (if there is one), also check limits on any tags (if any)
            if job_wrapper.job_destination.tags:
                for tag in job_wrapper.job_destination.tags:
                    # Check each tag for this job's destination
                    if tag in self.app.job_config.limits.destination_user_concurrent_jobs:
                        # Only if there's a limit defined for this tag
                        count = 0
                        for id in [ d.id for d in self.app.job_config.get_destinations(tag) ]:
                            # Add up the aggregate job total for this tag
                            count += count_per_id.get(id, 0)
                        if count >= self.app.job_config.limits.destination_user_concurrent_jobs[tag]:
                            return JOB_WAIT
        elif job.galaxy_session:
            # Anonymous users only get the hard limit
            if self.app.job_config.limits.anonymous_user_concurrent_jobs:
                count = self.sa_session.query( model.Job ).enable_eagerloads( False ) \
                            .filter( and_( model.Job.session_id == job.galaxy_session.id,
                                           or_( model.Job.state == model.Job.states.RUNNING,
                                                model.Job.state == model.Job.states.QUEUED ) ) ).count()
                if count >= self.app.job_config.limits.anonymous_user_concurrent_jobs:
                    return JOB_WAIT
        else:
            log.warning( 'Job %s is not associated with a user or session so job concurrency limit cannot be checked.' % job.id )
        return JOB_READY

    def __cache_total_job_count_per_destination( self ):
        # Cache the job count if necessary
        if self.total_job_count_per_destination is None:
            self.total_job_count_per_destination = {}
            result = self.sa_session.execute(select([model.Job.table.c.destination_id, func.count(model.Job.table.c.destination_id).label('job_count')]) \
                                            .where(and_(model.Job.table.c.state.in_((model.Job.states.QUEUED, model.Job.states.RUNNING)))) \
                                            .group_by(model.Job.table.c.destination_id))
            for row in result:
                self.total_job_count_per_destination[row['destination_id']] = row['job_count']

    def get_total_job_count_per_destination(self):
        self.__cache_total_job_count_per_destination()
        # Always use caching (at worst a job will have to wait one iteration,
        # and this would be more fair anyway as it ensures FIFO scheduling,
        # insofar as FIFO would be fair...)
        return self.total_job_count_per_destination

    def __check_destination_jobs( self, job, job_wrapper ):
        if self.app.job_config.limits.destination_total_concurrent_jobs:
            id = job_wrapper.job_destination.id
            count_per_id = self.get_total_job_count_per_destination()
            if id in self.app.job_config.limits.destination_total_concurrent_jobs:
                count = count_per_id.get(id, 0)
                # Check the number of dispatched jobs in the assigned destination id against the limit for that id
                if count >= self.app.job_config.limits.destination_total_concurrent_jobs[id]:
                    return JOB_WAIT
            # If we pass the destination limit (if there is one), also check limits on any tags (if any)
            if job_wrapper.job_destination.tags:
                for tag in job_wrapper.job_destination.tags:
                    # Check each tag for this job's destination
                    if tag in self.app.job_config.limits.destination_total_concurrent_jobs:
                        # Only if there's a limit defined for this tag
                        count = 0
                        for id in [ d.id for d in self.app.job_config.get_destinations(tag) ]:
                            # Add up the aggregate job total for this tag
                            count += count_per_id.get(id, 0)
                        if count >= self.app.job_config.limits.destination_total_concurrent_jobs[tag]:
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
                jobs_to_check.append( ( job, job.stderr ) )
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
        self.job_runners = self.app.job_config.get_job_runner_plugins( self.app.config.server_name )
        # Once plugins are loaded, all job destinations that were created from
        # URLs can have their URL params converted to the destination's param
        # dict by the plugin.
        self.app.job_config.convert_legacy_destinations(self.job_runners)
        log.debug( "Loaded job runners plugins: " + ':'.join( self.job_runners.keys() ) )

    def __get_runner_name( self, job_wrapper ):
        if job_wrapper.can_split():
            runner_name = "tasks"
        else:
            runner_name = job_wrapper.job_destination.runner
        return runner_name

    def url_to_destination( self, url ):
        """This is used by the runner mapper (a.k.a. dynamic runner) and
        recovery methods to have runners convert URLs to destinations.

        New-style runner plugin IDs must match the URL's scheme for this to work.
        """
        runner_name = url.split(':', 1)[0]
        try:
            return self.job_runners[runner_name].url_to_destination(url)
        except Exception, e:
            log.exception("Unable to convert legacy job runner URL '%s' to job destination, destination will be the '%s' runner with no params: %s" % (url, runner_name, e))
            return JobDestination(runner=runner_name)

    def put( self, job_wrapper ):
        runner_name = self.__get_runner_name( job_wrapper )
        try:
            if isinstance(job_wrapper, TaskWrapper):
                #DBTODO Refactor
                log.debug( "(%s) Dispatching task %s to %s runner" % ( job_wrapper.job_id, job_wrapper.task_id, runner_name ) )
            else:
                log.debug( "(%s) Dispatching to %s runner" % ( job_wrapper.job_id, runner_name ) )
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
            runner_name = ( job.get_job_runner_name().split( ":", 1 ) )[ 0 ]
            if ( isinstance( job, model.Job ) ):
                log.debug( "stopping job %d in %s runner" % ( job.get_id(), runner_name ) )
            elif ( isinstance( job, model.Task ) ):
                log.debug( "Stopping job %d, task %d in %s runner"
                         % ( job.get_job().get_id(), job.get_id(), runner_name ) )
            try:
                self.job_runners[runner_name].stop_job( job )
            except KeyError:
                log.error( 'stop(): (%s) Invalid job runner: %s' % ( job.get_id(), runner_name ) )
                # Job and output dataset states have already been updated, so nothing is done here.

    def recover( self, job, job_wrapper ):
        runner_name = ( job.job_runner_name.split(":", 1) )[0]
        log.debug( "recovering job %d in %s runner" % ( job.get_id(), runner_name ) )
        try:
            self.job_runners[runner_name].recover( job, job_wrapper )
        except KeyError:
            log.error( 'recover(): (%s) Invalid job runner: %s' % ( job_wrapper.job_id, runner_name ) )
            job_wrapper.fail( DEFAULT_JOB_PUT_FAILURE_MESSAGE )

    def shutdown( self ):
        for runner in self.job_runners.itervalues():
            runner.shutdown()

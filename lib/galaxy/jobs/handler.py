"""
Galaxy job handler, prepares, runs, tracks, and finishes Galaxy jobs
"""

import datetime
import os
import time
from collections import defaultdict
from queue import (
    Empty,
    Queue,
)
from typing import (
    Dict,
    List,
    Tuple,
    Type,
    Union,
)

from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import (
    and_,
    func,
    not_,
    null,
    or_,
    select,
    true,
)

from galaxy import model
from galaxy.exceptions import ObjectNotFound
from galaxy.jobs import (
    JobDestination,
    JobWrapper,
    TaskWrapper,
)
from galaxy.jobs.mapper import JobNotReadyException
from galaxy.managers.jobs import get_jobs_to_check_at_startup
from galaxy.model.base import (
    check_database_connection,
    transaction,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import unicodify
from galaxy.util.custom_logging import get_logger
from galaxy.util.monitors import Monitors
from galaxy.web_stack.handlers import HANDLER_ASSIGNMENT_METHODS

log = get_logger(__name__)

# States for running a job. These are NOT the same as data states
(
    JOB_WAIT,
    JOB_ERROR,
    JOB_INPUT_ERROR,
    JOB_INPUT_DELETED,
    JOB_READY,
    JOB_DELETED,
    JOB_ADMIN_DELETED,
    JOB_USER_OVER_QUOTA,
    JOB_USER_OVER_TOTAL_WALLTIME,
) = (
    "wait",
    "error",
    "input_error",
    "input_deleted",
    "ready",
    "deleted",
    "admin_deleted",
    "user_over_quota",
    "user_over_total_walltime",
)
DEFAULT_JOB_RUNNER_FAILURE_MESSAGE = "Unable to run job due to a misconfiguration of the Galaxy job running system.  Please contact a site administrator."


class JobHandlerI:
    def start(self):
        pass

    def shutdown(self):
        pass


class JobHandler(JobHandlerI):
    """
    Handle the preparation, running, tracking, and finishing of jobs
    """

    def __init__(self, app):
        self.app = app
        # The dispatcher launches the underlying job runners
        self.dispatcher = DefaultJobDispatcher(app)
        # Queues for starting and stopping jobs
        self.job_queue = JobHandlerQueue(app, self.dispatcher)
        self.job_stop_queue = JobHandlerStopQueue(app, self.dispatcher)

    def start(self):
        self.dispatcher.start()
        self.job_queue.start()
        self.job_stop_queue.start()

    def shutdown(self):
        self.job_queue.shutdown()
        self.job_stop_queue.shutdown()


class ItemGrabber:
    grab_model: Union[Type[model.Job], Type[model.WorkflowInvocation]]

    def __init__(
        self,
        app,
        handler_assignment_method=None,
        max_grab=None,
        self_handler_tags=None,
        handler_tags=None,
    ):
        self.app = app
        self.sa_session = app.model.context
        self.handler_assignment_method = handler_assignment_method
        self.self_handler_tags = self_handler_tags
        self.max_grab = max_grab
        self.handler_tags = handler_tags
        self._grab_query = None
        self._supports_returning = self.app.application_stack.supports_returning()

    def setup_query(self):
        if self.grab_model is model.Job:
            grab_condition = self.grab_model.state == self.grab_model.states.NEW
        elif self.grab_model is model.WorkflowInvocation:
            grab_condition = self.grab_model.state.in_(
                (
                    self.grab_model.states.NEW,
                    self.grab_model.states.REQUIRES_MATERIALIZATION,
                    self.grab_model.states.CANCELLING,
                )
            )
        else:
            raise NotImplementedError(f"Grabbing {self.grab_model.__name__} not implemented")
        subq = (
            select(self.grab_model.id)
            .where(
                and_(
                    self.grab_model.handler.in_(self.self_handler_tags),
                    grab_condition,
                )
            )
            .order_by(self.grab_model.id)
        )
        if self.max_grab:
            subq = subq.limit(self.max_grab)
        if self.handler_assignment_method == HANDLER_ASSIGNMENT_METHODS.DB_SKIP_LOCKED:
            subq = subq.with_for_update(skip_locked=True)
        self._grab_query = (
            self.grab_model.table.update()
            .where(self.grab_model.id.in_(subq))
            .values(handler=self.app.config.server_name)
        )
        if self._supports_returning:
            self._grab_query = self._grab_query.returning(self.grab_model.id)
        if self.handler_assignment_method == HANDLER_ASSIGNMENT_METHODS.DB_TRANSACTION_ISOLATION:
            self._grab_conn_opts["isolation_level"] = "SERIALIZABLE"
        log.info(
            "Handler job grabber initialized with '%s' assignment method for handler '%s', tag(s): %s",
            self.handler_assignment_method,
            self.app.config.server_name,
            ", ".join(str(x) for x in self.handler_tags),
        )

    @staticmethod
    def get_grabbable_handler_assignment_method(handler_assignment_methods):
        grabbable_methods = {
            HANDLER_ASSIGNMENT_METHODS.DB_TRANSACTION_ISOLATION,
            HANDLER_ASSIGNMENT_METHODS.DB_SKIP_LOCKED,
        }
        if handler_assignment_methods:
            try:
                return [m for m in handler_assignment_methods if m in grabbable_methods][0]
            except IndexError:
                return

    def grab_unhandled_items(self):
        """
        Attempts to assign unassigned jobs or invocaions to itself using DB serialization methods, if enabled. This
        simply sets `Job.handler` or `WorkflowInvocation.handler` to the current server name, which causes the job to be picked up by
        the appropriate handler.
        """
        # an excellent discussion on PostgreSQL concurrency safety:
        # https://blog.2ndquadrant.com/what-is-select-skip-locked-for-in-postgresql-9-5/
        if self._grab_query is None:
            self.setup_query()

        with self.app.model.engine.connect() as conn:
            with conn.begin() as trans:
                try:
                    proxy = conn.execute(self._grab_query)
                    if self._supports_returning:
                        rows = proxy.fetchall()
                        if rows:
                            log.debug(
                                f"Grabbed {self.grab_model.__name__}(s): {', '.join(str(row[0]) for row in rows)}"
                            )
                        else:
                            trans.rollback()
                except OperationalError as e:
                    # If this is a serialization failure on PostgreSQL, then e.orig is a psycopg2 TransactionRollbackError
                    # and should have attribute `code`. Other engines should just report the message and move on.
                    if int(getattr(e.orig, "pgcode", -1)) != 40001:
                        log.debug(
                            "Grabbing %s failed (serialization failures are ok): %s",
                            self.grab_model.__name__,
                            unicodify(e),
                        )
                    trans.rollback()


class InvocationGrabber(ItemGrabber):
    grab_model = model.WorkflowInvocation


class JobGrabber(ItemGrabber):
    grab_model = model.Job


class StopSignalException(Exception):
    """Exception raised when queue returns a stop signal."""


class BaseJobHandlerQueue(Monitors):
    STOP_SIGNAL = object()

    def __init__(self, app: MinimalManagerApp, dispatcher: "DefaultJobDispatcher"):
        """
        Initializes the Queue, creates (unstarted) monitoring thread.
        """
        self.app = app
        self.dispatcher = dispatcher
        self.sa_session = app.model.context  # scoped session registry
        self.track_jobs_in_database = self.app.config.track_jobs_in_database
        # Keep track of the pid that started the job manager, only it has valid threads
        self.parent_pid = os.getpid()
        # This queue is not used if track_jobs_in_database is True.
        self.queue: Queue[Tuple[int, str]] = Queue()


class JobHandlerQueue(BaseJobHandlerQueue):
    """
    Job Handler's Internal Queue, this is what actually implements waiting for
    jobs to be runnable and dispatching to a JobRunner.
    """

    def __init__(self, app: MinimalManagerApp, dispatcher):
        super().__init__(app, dispatcher)
        # self.queue contains tuples: (job_id, tool_id)

        # Initialize structures for handling job limits
        self.__clear_job_count()
        # Contains job ids for jobs that are waiting (only use from monitor thread)
        self.waiting_jobs: List[int] = []
        # Contains wrappers of jobs that are limited or ready (so they aren't created unnecessarily/multiple times)
        self.job_wrappers: Dict[int, JobWrapper] = {}
        name = "JobHandlerQueue.monitor_thread"
        self._init_monitor_thread(name, target=self.__monitor, config=app.config)
        self.job_grabber = None
        handler_assignment_method = JobGrabber.get_grabbable_handler_assignment_method(
            self.app.job_config.handler_assignment_methods
        )
        if handler_assignment_method:
            self.job_grabber = JobGrabber(
                app=app,
                handler_assignment_method=handler_assignment_method,
                max_grab=self.app.job_config.handler_max_grab,
                self_handler_tags=self.app.job_config.self_handler_tags,
                handler_tags=self.app.job_config.handler_tags,
            )

    def start(self):
        """
        Starts the JobHandler's thread after checking for any unhandled jobs.
        """
        log.debug("Handler queue starting for jobs assigned to handler: %s", self.app.config.server_name)
        # Recover jobs at startup
        self.__check_jobs_at_startup()
        # Start the queue
        self.monitor_thread.start()
        log.info("job handler queue started")

    def job_wrapper(self, job, use_persisted_destination=False):
        return JobWrapper(job, self, use_persisted_destination=use_persisted_destination)

    def job_pair_for_id(self, id):
        job = self.sa_session.query(model.Job).get(id)
        return job, self.job_wrapper(job, use_persisted_destination=True)

    def __check_jobs_at_startup(self):
        """
        Checks all jobs that are in the 'new', 'queued', 'running', or 'stopped' state in
        the database and requeues or cleans up as necessary. Only run as the job handler starts.
        In case the activation is enforced it will filter out the jobs of inactive users.
        """
        with self.sa_session() as session:
            for job in get_jobs_to_check_at_startup(session, self.track_jobs_in_database, self.app.config):
                try:
                    self._check_job_at_startup(job)
                except Exception:
                    log.exception("Error while recovering job %s during application startup.", job.id)
            with transaction(session):
                session.commit()

    def _check_job_at_startup(self, job: model.Job):
        assert job.tool_id is not None
        if not self.app.toolbox.has_tool(job.tool_id, job.tool_version, exact=True):
            log.warning(f"({job.id}) Tool '{job.tool_id}' removed from tool config, unable to recover job")
            self.job_wrapper(job).fail(
                "This tool was disabled before the job completed.  Please contact your Galaxy administrator."
            )
        elif job.copied_from_job_id:
            self.queue.put((job.id, job.tool_id))
        elif job.job_runner_name is not None and job.job_runner_external_id is None:
            # This could happen during certain revisions of Galaxy where a runner URL was persisted before the job was dispatched to a runner.
            log.debug(f"({job.id}) Job runner assigned but no external ID recorded, adding to the job handler queue")
            job.job_runner_name = None
            if self.track_jobs_in_database:
                job.set_state(model.Job.states.NEW)
            else:
                self.queue.put((job.id, job.tool_id))
        elif job.job_runner_name is not None and job.job_runner_external_id is not None and job.destination_id is None:
            # This is the first start after upgrading from URLs to destinations, convert the URL to a destination and persist
            job_wrapper = self.job_wrapper(job)
            job_destination = self.dispatcher.url_to_destination(job.job_runner_name)
            if job_destination.id is None:
                job_destination.id = "legacy_url"
            job_wrapper.set_job_destination(job_destination, job.job_runner_external_id)
            self.dispatcher.recover(job, job_wrapper)
            log.info(f"({job.id}) Converted job from a URL to a destination and recovered")
        elif job.job_runner_name is None:
            # Never (fully) dispatched
            log.debug(
                f"({job.id}) No job runner assigned and job still in '{job.state}' state, adding to the job handler queue"
            )
            if self.track_jobs_in_database:
                job.set_state(model.Job.states.NEW)
            else:
                self.queue.put((job.id, job.tool_id))
        else:
            # Already dispatched and running
            job_wrapper = self.__recover_job_wrapper(job)
            self.dispatcher.recover(job, job_wrapper)
        pass

    def __recover_job_wrapper(self, job):
        # Already dispatched and running
        job_wrapper = self.job_wrapper(job)
        # Use the persisted destination as its params may differ from
        # what's in the job config
        job_destination = JobDestination(
            id=job.destination_id, runner=job.job_runner_name, params=job.destination_params
        )
        # resubmits are not persisted (it's a good thing) so they
        # should be added back to the in-memory destination on startup
        try:
            config_job_destination = self.app.job_config.get_destination(job.destination_id)
            job_destination.resubmit = config_job_destination.resubmit
        except KeyError:
            log.debug(
                "(%s) Recovered destination id (%s) does not exist in job config (but this may be normal in the case of a dynamically generated destination)",
                job.id,
                job.destination_id,
            )
        job_wrapper.job_runner_mapper.cached_job_destination = job_destination
        return job_wrapper

    def __monitor(self):
        """
        Continually iterate the waiting jobs, checking is each is ready to
        run and dispatching if so.
        """
        while self.monitor_running:
            try:
                # If jobs are locked, there's nothing to monitor and we skip
                # to the sleep.
                if not self.app.job_manager.job_lock:
                    self.__monitor_step()
            except Exception:
                log.exception("Exception in monitor_step")
                # With sqlite backends we can run into locked databases occasionally
                # To avoid that the monitor step locks again we backoff a little longer.
                self._monitor_sleep(5)
            self._monitor_sleep(self.app.config.job_handler_monitor_sleep)

    def __monitor_step(self):
        """
        Called repeatedly by `monitor` to process waiting jobs.
        """
        monitor_step_timer = self.app.execution_timer_factory.get_timer(
            "internal.galaxy.jobs.handlers.monitor_step", "Job handler monitor step complete."
        )
        if self.job_grabber is not None:
            self.job_grabber.grab_unhandled_items()
        try:
            self.__handle_waiting_jobs()
        except StopSignalException:
            pass
        finally:
            self.sa_session.remove()
        log.trace(monitor_step_timer.to_str())

    def __handle_waiting_jobs(self):
        """
        Gets any new jobs (either from the database or from its own queue), then iterates over all new and waiting jobs
        to check the state of the jobs each depends on. If the job has dependencies that have not finished, it goes to
        the waiting queue. If the job has dependencies with errors, it is marked as having errors and removed from the
        queue. If the job belongs to an inactive user it is ignored.  Otherwise, the job is dispatched.
        """
        check_database_connection(self.sa_session)
        # Pull all new jobs from the queue at once
        jobs_to_check = []
        resubmit_jobs = []
        if self.track_jobs_in_database:
            # Clear the session so we get fresh states for job and all datasets
            self.sa_session.expunge_all()
            # Fetch all new jobs
            hda_not_ready = (
                self.sa_session.query(model.Job.id)
                .enable_eagerloads(False)
                .join(model.JobToInputDatasetAssociation)
                .join(model.HistoryDatasetAssociation)
                .join(model.Dataset)
                .filter(
                    and_(
                        model.Job.state == model.Job.states.NEW, model.Dataset.state.in_(model.Dataset.non_ready_states)
                    )
                )
                .subquery()
            )
            ldda_not_ready = (
                self.sa_session.query(model.Job.id)
                .enable_eagerloads(False)
                .join(model.JobToInputLibraryDatasetAssociation)
                .join(model.LibraryDatasetDatasetAssociation)
                .join(model.Dataset)
                .filter(
                    and_(
                        model.Job.state == model.Job.states.NEW, model.Dataset.state.in_(model.Dataset.non_ready_states)
                    )
                )
                .subquery()
            )
            coalesce_exp = func.coalesce(
                model.Job.table.c.user_id, model.Job.table.c.session_id
            )  # accommodate jobs by anonymous users
            rank = func.rank().over(partition_by=coalesce_exp, order_by=model.Job.table.c.id).label("rank")
            job_filter_conditions = (
                (model.Job.state == model.Job.states.NEW),
                (model.Job.handler == self.app.config.server_name),
                ~model.Job.table.c.id.in_(select(hda_not_ready)),
                ~model.Job.table.c.id.in_(select(ldda_not_ready)),
            )
            if self.app.config.user_activation_on:
                job_filter_conditions = job_filter_conditions + (
                    or_((model.Job.user_id == null()), (model.User.active == true())),
                )
            if self.sa_session.bind.name == "sqlite":
                query_objects = (model.Job,)
            else:
                query_objects = (model.Job, rank)
            ready_query = (
                self.sa_session.query(*query_objects)
                .enable_eagerloads(False)
                .outerjoin(model.User)
                .filter(and_(*job_filter_conditions))
                .order_by(model.Job.id)
            )
            if self.sa_session.bind.name == "sqlite":
                jobs_to_check = ready_query.all()
            else:
                ranked = ready_query.subquery()
                jobs_to_check = (
                    self.sa_session.query(model.Job)
                    .join(ranked, model.Job.id == ranked.c.id)
                    .filter(ranked.c.rank <= self.app.job_config.handler_ready_window_size)
                    .all()
                )
            # Filter jobs with invalid input states
            jobs_to_check = self.__filter_jobs_with_invalid_input_states(jobs_to_check)
            # Fetch all "resubmit" jobs
            resubmit_jobs = (
                self.sa_session.query(model.Job)
                .enable_eagerloads(False)
                .filter(
                    and_(
                        (model.Job.state == model.Job.states.RESUBMITTED),
                        (model.Job.handler == self.app.config.server_name),
                    )
                )
                .order_by(model.Job.id)
                .all()
            )
        else:
            # Get job objects and append to watch queue for any which were
            # previously waiting
            for job_id in self.waiting_jobs:
                jobs_to_check.append(self.sa_session.query(model.Job).get(job_id))
            try:
                while 1:
                    message = self.queue.get_nowait()
                    if message is self.STOP_SIGNAL:
                        raise StopSignalException()
                    # Unpack the message
                    job_id, tool_id = message
                    # Get the job object and append to watch queue
                    jobs_to_check.append(self.sa_session.query(model.Job).get(job_id))
            except Empty:
                pass
        # Ensure that we get new job counts on each iteration
        self.__clear_job_count()
        # Check resubmit jobs first so that limits of new jobs will still be enforced
        for job in resubmit_jobs:
            log.debug("(%s) Job was resubmitted and is being dispatched immediately", job.id)
            # Reassemble resubmit job destination from persisted value
            jw = self.__recover_job_wrapper(job)
            if jw.is_ready_for_resubmission(job):
                self.increase_running_job_count(job.user_id, jw.job_destination.id)
                self.dispatcher.put(jw)
        # Iterate over new and waiting jobs and look for any that are
        # ready to run
        new_waiting_jobs = []
        for job in jobs_to_check:
            try:
                # Check the job's dependencies, requeue if they're not done.
                # Some of these states will only happen when using the in-memory job queue
                if job.copied_from_job_id:
                    copied_from_job = self.sa_session.query(model.Job).get(job.copied_from_job_id)
                    job.numeric_metrics = copied_from_job.numeric_metrics
                    job.text_metrics = copied_from_job.text_metrics
                    job.dependencies = copied_from_job.dependencies
                    job.state = copied_from_job.state
                    job.job_stderr = copied_from_job.job_stderr
                    job.job_stdout = copied_from_job.job_stdout
                    job.tool_stderr = copied_from_job.tool_stderr
                    job.tool_stdout = copied_from_job.tool_stdout
                    job.command_line = copied_from_job.command_line
                    job.traceback = copied_from_job.traceback
                    job.tool_version = copied_from_job.tool_version
                    job.exit_code = copied_from_job.exit_code
                    job.job_runner_name = copied_from_job.job_runner_name
                    job.job_runner_external_id = copied_from_job.job_runner_external_id
                    continue
                job_state = self.__check_job_state(job)
                if job_state == JOB_WAIT:
                    new_waiting_jobs.append(job.id)
                elif job_state == JOB_INPUT_ERROR:
                    log.info("(%d) Job unable to run: one or more inputs in error state" % job.id)
                elif job_state == JOB_INPUT_DELETED:
                    log.info("(%d) Job unable to run: one or more inputs deleted" % job.id)
                elif job_state == JOB_READY:
                    self.dispatcher.put(self.job_wrappers.pop(job.id))
                    log.info("(%d) Job dispatched" % job.id)
                elif job_state == JOB_DELETED:
                    log.info("(%d) Job deleted by user while still queued" % job.id)
                elif job_state == JOB_ADMIN_DELETED:
                    log.info("(%d) Job deleted by admin while still queued" % job.id)
                elif job_state == JOB_USER_OVER_TOTAL_WALLTIME:
                    log.info("(%d) User (%s) is over total walltime limit: job paused" % (job.id, job.user_id))
                    job.set_state(model.Job.states.PAUSED)
                    for dataset_assoc in job.output_datasets + job.output_library_datasets:
                        dataset_assoc.dataset.dataset.state = model.Dataset.states.PAUSED
                        dataset_assoc.dataset.info = "Execution of this dataset's job is paused because you were over your total job runtime at the time it was ready to run"
                        self.sa_session.add(dataset_assoc.dataset.dataset)
                    self.sa_session.add(job)
                elif job_state == JOB_ERROR:
                    # A more informative message is shown wherever the job state is set to error
                    pass
                else:
                    log.error("(%d) Job in unknown state '%s'" % (job.id, job_state))
                    new_waiting_jobs.append(job.id)
            except Exception:
                log.exception("failure running job %d", job.id)
        # Update the waiting list
        if not self.track_jobs_in_database:
            self.waiting_jobs = new_waiting_jobs
        # Remove cached wrappers for any jobs that are no longer being tracked
        for id in set(self.job_wrappers.keys()) - set(new_waiting_jobs):
            del self.job_wrappers[id]
        # Commit updated state
        with transaction(self.sa_session):
            self.sa_session.commit()

    def __filter_jobs_with_invalid_input_states(self, jobs):
        """
        Takes  list of jobs and filters out jobs whose input datasets are in invalid state and
        set these jobs and their dependent jobs to paused.
        """
        job_ids_to_check = [j.id for j in jobs]
        queries = []
        for job_to_input, input_association in [
            (model.JobToInputDatasetAssociation, model.HistoryDatasetAssociation),
            (model.JobToInputLibraryDatasetAssociation, model.LibraryDatasetDatasetAssociation),
        ]:
            q = (
                self.sa_session.query(
                    model.Job.id,
                    input_association.deleted,
                    input_association._state,
                    input_association.name,
                    model.Dataset.deleted,
                    model.Dataset.purged,
                    model.Dataset.state,
                )
                .join(job_to_input.job)
                .join(input_association)
                .join(model.Dataset)
                .filter(model.Job.id.in_(job_ids_to_check))
                .filter(
                    or_(
                        model.Dataset.deleted == true(),
                        not_(
                            or_(
                                model.Dataset.state == model.Dataset.states.OK,
                                model.Dataset.state == model.Dataset.states.DEFERRED,
                            )
                        ),
                        input_association.deleted == true(),
                        input_association._state.in_(
                            (input_association.states.FAILED_METADATA, input_association.states.SETTING_METADATA)
                        ),
                    )
                )
                .all()
            )
            queries.extend(q)
        jobs_to_pause = defaultdict(list)
        jobs_to_fail = defaultdict(list)
        jobs_to_ignore = defaultdict(list)
        for job_id, hda_deleted, hda_state, hda_name, dataset_deleted, dataset_purged, dataset_state in queries:
            if hda_deleted or dataset_deleted:
                if dataset_purged:
                    # If the dataset has been purged we can't resume the job by undeleting the input
                    jobs_to_fail[job_id].append(f"Input dataset '{hda_name}' was deleted before the job started")
                else:
                    jobs_to_pause[job_id].append(f"Input dataset '{hda_name}' was deleted before the job started")
            elif hda_state == model.HistoryDatasetAssociation.states.FAILED_METADATA:
                jobs_to_pause[job_id].append(f"Input dataset '{hda_name}' failed to properly set metadata")
            elif dataset_state == model.Dataset.states.PAUSED:
                jobs_to_pause[job_id].append(f"Input dataset '{hda_name}' was paused before the job started")
            elif dataset_state == model.Dataset.states.ERROR:
                jobs_to_pause[job_id].append(f"Input dataset '{hda_name}' is in error state")
            elif dataset_state != model.Dataset.states.OK:
                jobs_to_ignore[job_id].append(f"Input dataset '{hda_name}' is in {dataset_state} state")
        for job_id in sorted(jobs_to_pause):
            pause_message = ", ".join(jobs_to_pause[job_id])
            pause_message = f"{pause_message}. To resume this job fix the input dataset(s)."
            job, job_wrapper = self.job_pair_for_id(job_id)
            try:
                job_wrapper.pause(job=job, message=pause_message)
            except Exception:
                log.exception("(%s) Caught exception while attempting to pause job.", job_id)
        for job_id in sorted(jobs_to_fail):
            fail_message = ", ".join(jobs_to_fail[job_id])
            job, job_wrapper = self.job_pair_for_id(job_id)
            try:
                job_wrapper.fail(fail_message)
            except Exception:
                log.exception("(%s) Caught exception while attempting to fail job.", job_id)
        jobs_to_ignore.update(jobs_to_pause)
        jobs_to_ignore.update(jobs_to_fail)
        return [j for j in jobs if j.id not in jobs_to_ignore]

    def __check_job_state(self, job):
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
            in_memory_not_ready_state = self.__verify_in_memory_job_inputs(job)
            if in_memory_not_ready_state:
                return in_memory_not_ready_state

        # Else, if tracking in the database, job.state is guaranteed to be NEW and
        # the inputs are guaranteed to be OK.

        # Create the job wrapper so that the destination can be set
        job_id = job.id
        job_wrapper = self.job_wrappers.get(job_id, None)
        if not job_wrapper:
            job_wrapper = self.job_wrapper(job)
            self.job_wrappers[job_id] = job_wrapper

        # If state == JOB_READY, assume job_destination also set - otherwise
        # in case of various error or cancelled states do not assume
        # destination has been set.
        state, job_destination = self.__verify_job_ready(job, job_wrapper)

        if state == JOB_READY:
            # PASS.  increase usage by one job (if caching) so that multiple jobs aren't dispatched on this queue iteration
            self.increase_running_job_count(job.user_id, job_destination.id)
            for job_to_input_dataset_association in job.input_datasets:
                # We record the input dataset version, now that we know the inputs are ready
                if job_to_input_dataset_association.dataset:
                    job_to_input_dataset_association.dataset_version = job_to_input_dataset_association.dataset.version
        return state

    def __verify_job_ready(self, job, job_wrapper):
        """Compute job destination and verify job is ready at that
        destination by checking job limits and quota. If this method
        return a job state of JOB_READY - it MUST also return a job
        destination.
        """
        job_destination = None
        try:
            assert (
                job_wrapper.tool is not None
            ), "This tool was disabled before the job completed.  Please contact your Galaxy administrator."
            # Cause the job_destination to be set and cached by the mapper
            job_destination = job_wrapper.job_destination
        except AssertionError as e:
            log.warning(f"({job.id}) Tool '{job.tool_id}' removed from tool config, unable to run job")
            job_wrapper.fail(e)
            return JOB_ERROR, job_destination
        except JobNotReadyException as e:
            job_state = e.job_state or JOB_WAIT
            return job_state, None
        except Exception as e:
            failure_message = getattr(e, "failure_message", DEFAULT_JOB_RUNNER_FAILURE_MESSAGE)
            if failure_message == DEFAULT_JOB_RUNNER_FAILURE_MESSAGE:
                log.exception("Failed to generate job destination")
            else:
                log.debug(f"Intentionally failing job with message ({failure_message})")
            job_wrapper.fail(failure_message)
            return JOB_ERROR, job_destination
        # job is ready to run, check limits
        # TODO: these checks should be refactored to minimize duplication and made more modular/pluggable
        state = self.__check_destination_jobs(job, job_wrapper)

        if state == JOB_READY:
            state = self.__check_user_jobs(job, job_wrapper)
        # Check total walltime limits
        if state == JOB_READY and "delta" in self.app.job_config.limits.total_walltime:
            jobs_to_check = self.sa_session.query(model.Job).filter(
                model.Job.update_time
                >= datetime.datetime.now() - datetime.timedelta(self.app.job_config.limits.total_walltime["window"]),
                model.Job.state == "ok",
            )
            if job.user_id:
                jobs_to_check = jobs_to_check.filter(model.Job.user_id == job.user_id)
            else:
                jobs_to_check = jobs_to_check.filter(model.Job.session_id == job.session_id)
            time_spent = datetime.timedelta(0)
            for job in jobs_to_check:
                # History is job.state_history
                started = None
                finished = None
                for history in sorted(job.state_history, key=lambda h: h.create_time):
                    if history.state == "running":
                        started = history.create_time
                    elif history.state == "ok":
                        finished = history.create_time

                if started is not None and finished is not None:
                    time_spent += finished - started
                else:
                    log.warning(
                        "Unable to calculate time spent for job %s; started: %s, finished: %s",
                        job.id,
                        started,
                        finished,
                    )

            if time_spent > self.app.job_config.limits.total_walltime["delta"]:
                return JOB_USER_OVER_TOTAL_WALLTIME, job_destination

        return state, job_destination

    def __verify_in_memory_job_inputs(self, job):
        """Perform the same checks that happen via SQL for in-memory managed
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
                self.job_wrappers.pop(job.id, self.job_wrapper(job)).fail(
                    f"input data {idata.hid} (file: {idata.get_file_name()}) was deleted before the job started"
                )
                return JOB_INPUT_DELETED
            # an error in the input data causes us to bail immediately
            elif idata.state == idata.states.ERROR:
                self.job_wrappers.pop(job.id, self.job_wrapper(job)).fail(f"input data {idata.hid} is in error state")
                return JOB_INPUT_ERROR
            elif idata.state == idata.states.FAILED_METADATA:
                self.job_wrappers.pop(job.id, self.job_wrapper(job)).fail(
                    f"input data {idata.hid} failed to properly set metadata"
                )
                return JOB_INPUT_ERROR
            elif idata.state != idata.states.OK and not (
                idata.state == idata.states.SETTING_METADATA
                and job.tool_id is not None
                and job.tool_id == self.app.datatypes_registry.set_external_metadata_tool.id
            ):
                # need to requeue
                return JOB_WAIT

        # All inputs ready to go.
        return None

    def __clear_job_count(self):
        self.user_job_count = None
        self.user_job_count_per_destination = None
        self.total_job_count_per_destination = None

    def get_user_job_count(self, user_id):
        self.__cache_user_job_count()
        # This could have been incremented by a previous job dispatched on this iteration, even if we're not caching
        rval = self.user_job_count.get(user_id, 0)
        if not self.app.config.cache_user_job_count:
            result = self.sa_session.execute(
                select(func.count(model.Job.table.c.id)).where(
                    and_(
                        model.Job.table.c.state.in_(
                            (model.Job.states.QUEUED, model.Job.states.RUNNING, model.Job.states.RESUBMITTED)
                        ),
                        (model.Job.table.c.user_id == user_id),
                    )
                )
            )
            for row in result:
                # there should only be one row
                rval += row[0]
        return rval

    def __cache_user_job_count(self):
        # Cache the job count if necessary
        if self.user_job_count is None and self.app.config.cache_user_job_count:
            self.user_job_count = {}
            query = self.sa_session.execute(
                select(model.Job.table.c.user_id, func.count(model.Job.table.c.user_id))
                .where(
                    and_(
                        model.Job.table.c.state.in_(
                            (model.Job.states.QUEUED, model.Job.states.RUNNING, model.Job.states.RESUBMITTED)
                        ),
                        (model.Job.table.c.user_id != null()),
                    )
                )
                .group_by(model.Job.table.c.user_id)
            )
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
            result = self.sa_session.execute(
                select(
                    model.Job.table.c.destination_id, func.count(model.Job.table.c.destination_id).label("job_count")
                )
                .where(
                    and_(
                        model.Job.table.c.state.in_((model.Job.states.QUEUED, model.Job.states.RUNNING)),
                        (model.Job.table.c.user_id == user_id),
                    )
                )
                .group_by(model.Job.table.c.destination_id)
            )
            for row in result.mappings():
                # Add the count from the database to the cached count
                rval[row["destination_id"]] = rval.get(row["destination_id"], 0) + row["job_count"]
        return rval

    def __cache_user_job_count_per_destination(self):
        # Cache the job count if necessary
        if self.user_job_count_per_destination is None and self.app.config.cache_user_job_count:
            self.user_job_count_per_destination = {}
            result = self.sa_session.execute(
                select(
                    model.Job.table.c.user_id,
                    model.Job.table.c.destination_id,
                    func.count(model.Job.table.c.user_id).label("job_count"),
                )
                .where(and_(model.Job.table.c.state.in_((model.Job.states.QUEUED, model.Job.states.RUNNING))))
                .group_by(model.Job.table.c.user_id, model.Job.table.c.destination_id)
            )
            for row in result.mappings():
                if row["user_id"] not in self.user_job_count_per_destination:
                    self.user_job_count_per_destination[row["user_id"]] = {}
                self.user_job_count_per_destination[row["user_id"]][row["destination_id"]] = row["job_count"]
        elif self.user_job_count_per_destination is None:
            self.user_job_count_per_destination = {}

    def increase_running_job_count(self, user_id, destination_id):
        if (
            self.app.job_config.limits.registered_user_concurrent_jobs
            or self.app.job_config.limits.anonymous_user_concurrent_jobs
            or self.app.job_config.limits.destination_user_concurrent_jobs
        ):
            if self.user_job_count is None:
                self.user_job_count = {}
            if self.user_job_count_per_destination is None:
                self.user_job_count_per_destination = {}
            self.user_job_count[user_id] = self.user_job_count.get(user_id, 0) + 1
            if user_id not in self.user_job_count_per_destination:
                self.user_job_count_per_destination[user_id] = {}
            self.user_job_count_per_destination[user_id][destination_id] = (
                self.user_job_count_per_destination[user_id].get(destination_id, 0) + 1
            )
        if self.app.job_config.limits.destination_total_concurrent_jobs:
            if self.total_job_count_per_destination is None:
                self.total_job_count_per_destination = {}
            self.total_job_count_per_destination[destination_id] = (
                self.total_job_count_per_destination.get(destination_id, 0) + 1
            )

    def __check_user_jobs(self, job, job_wrapper):
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
                        for id in [d.id for d in self.app.job_config.get_destinations(tag)]:
                            # Add up the aggregate job total for this tag
                            count += count_per_id.get(id, 0)
                        if count >= self.app.job_config.limits.destination_user_concurrent_jobs[tag]:
                            return JOB_WAIT
        elif job.galaxy_session:
            # Anonymous users only get the hard limit
            if self.app.job_config.limits.anonymous_user_concurrent_jobs:
                count = (
                    self.sa_session.query(model.Job)
                    .enable_eagerloads(False)
                    .filter(
                        and_(
                            model.Job.session_id == job.galaxy_session.id,
                            or_(
                                model.Job.state == model.Job.states.RUNNING, model.Job.state == model.Job.states.QUEUED
                            ),
                        )
                    )
                    .count()
                )
                if count >= self.app.job_config.limits.anonymous_user_concurrent_jobs:
                    return JOB_WAIT
        else:
            log.warning(
                f"Job {job.id} is not associated with a user or session so job concurrency limit cannot be checked."
            )
        return JOB_READY

    def __cache_total_job_count_per_destination(self):
        # Cache the job count if necessary
        if self.total_job_count_per_destination is None:
            self.total_job_count_per_destination = {}
            result = self.sa_session.execute(
                select(
                    model.Job.table.c.destination_id, func.count(model.Job.table.c.destination_id).label("job_count")
                )
                .where(and_(model.Job.table.c.state.in_((model.Job.states.QUEUED, model.Job.states.RUNNING))))
                .group_by(model.Job.table.c.destination_id)
            )
            for row in result.mappings():
                self.total_job_count_per_destination[row["destination_id"]] = row["job_count"]

    def get_total_job_count_per_destination(self):
        self.__cache_total_job_count_per_destination()
        # Always use caching (at worst a job will have to wait one iteration,
        # and this would be more fair anyway as it ensures FIFO scheduling,
        # insofar as FIFO would be fair...)
        return self.total_job_count_per_destination

    def __check_destination_jobs(self, job, job_wrapper):
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
                        for id in [d.id for d in self.app.job_config.get_destinations(tag)]:
                            # Add up the aggregate job total for this tag
                            count += count_per_id.get(id, 0)
                        if count >= self.app.job_config.limits.destination_total_concurrent_jobs[tag]:
                            return JOB_WAIT
        return JOB_READY

    def put(self, job_id, tool_id):
        """Add a job to the queue (by job identifier)"""
        if not self.track_jobs_in_database:
            self.queue.put((job_id, tool_id))
            self.sleeper.wake()

    def shutdown(self):
        """Attempts to gracefully shut down the worker thread"""
        if self.parent_pid != os.getpid():
            # We're not the real job queue, do nothing
            return
        else:
            log.info("sending stop signal to worker thread")
            self.stop_monitoring()
            if not self.track_jobs_in_database:
                self.queue.put(self.STOP_SIGNAL)
            # A message could still be received while shutting down, should be ok since they will be picked up on next startup.
            self.sleeper.wake()
            self.shutdown_monitor()
            log.info("job handler queue stopped")
            self.dispatcher.shutdown()


class JobHandlerStopQueue(BaseJobHandlerQueue):
    """
    A queue for jobs which need to be terminated prematurely.
    """

    def __init__(self, app: MinimalManagerApp, dispatcher):
        super().__init__(app, dispatcher)
        # self.queue contains tuples: (job_id, error message)

        name = "JobHandlerStopQueue.monitor_thread"
        self._init_monitor_thread(name, target=self.__monitor, config=app.config)

    def start(self):
        # Start the queue
        self.monitor_thread.start()
        log.info("job handler stop queue started")

    def __monitor(self):
        """
        Continually iterate and stop appropriate jobs.
        """
        # HACK: Delay until after forking, we need a way to do post fork notification!!!
        time.sleep(10)
        while self.monitor_running:
            try:
                self.__monitor_step()
            except Exception:
                log.exception("Exception in monitor_step")
            # Sleep
            self._monitor_sleep(1)

    def __delete(self, job, error_msg, session):
        final_state = job.states.DELETED
        if error_msg is not None:
            final_state = job.states.ERROR
            job.info = error_msg
        job.set_final_state(final_state, supports_skip_locked=self.app.application_stack.supports_skip_locked())
        session.add(job)
        session.flush()

    def __stop(self, job, session):
        job.set_state(job.states.STOPPED)
        session.add(job)
        session.flush()

    def __monitor_step(self):
        """
        Called repeatedly by `monitor` to stop jobs.
        """
        # Pull all new jobs from the queue at once
        jobs_to_check = []
        with self.sa_session() as session, session.begin():
            self._add_newly_deleted_jobs(session, jobs_to_check)
            try:
                self._pull_from_queue(session, jobs_to_check)
            except StopSignalException:
                return
            self._check_jobs(session, jobs_to_check)

    def put(self, job_id, error_msg=None):
        if not self.track_jobs_in_database:
            self.queue.put((job_id, error_msg))

    def shutdown(self):
        """Attempts to gracefully shut down the worker thread"""
        if self.parent_pid != os.getpid():
            # We're not the real job queue, do nothing
            return
        else:
            log.info("sending stop signal to worker thread")
            self.stop_monitoring()
            if not self.track_jobs_in_database:
                self.queue.put(self.STOP_SIGNAL)
            self.shutdown_monitor()
            log.info("job handler stop queue stopped")

    def _add_newly_deleted_jobs(self, session, jobs_to_check):
        if self.track_jobs_in_database:
            newly_deleted_jobs = self._get_new_jobs(session)
            for job in newly_deleted_jobs:
                # job.stderr is always a string (job.job_stderr + job.tool_stderr, possibly `''`),
                # while any `not None` message returned in self.queue.get_nowait() is interpreted
                # as an error, so here we use None if job.stderr is false-y
                jobs_to_check.append((job, job.stderr or None))

    def _get_new_jobs(self, session):
        states = (model.Job.states.DELETING, model.Job.states.STOPPING)
        stmt = select(model.Job).filter(
            model.Job.state.in_(states) & (model.Job.handler == self.app.config.server_name)
        )
        return session.scalars(stmt).all()

    def _pull_from_queue(self, session, jobs_to_check):
        # Pull jobs from the queue (in the case of Administrative stopped jobs)
        try:
            while 1:
                message = self.queue.get_nowait()
                if message is self.STOP_SIGNAL:
                    raise StopSignalException()
                job_id, error_msg = message
                job = session.get(model.Job, job_id)
                jobs_to_check.append((job, error_msg))
        except Empty:
            pass

    def _check_jobs(self, session, jobs_to_check):
        for job, error_msg in jobs_to_check:
            if (
                job.state
                not in (
                    job.states.DELETING,
                    job.states.DELETED,
                    job.states.STOPPING,
                    job.states.STOPPED,
                )
                and job.finished
            ):
                # terminated before it got here
                log.debug("Job %s already finished, not deleting or stopping", job.id)
                continue
            if job.state == job.states.DELETING:
                self.__delete(job, error_msg, session)
            elif job.state == job.states.STOPPING:
                self.__stop(job, session)
            if job.job_runner_name is not None:
                # tell the dispatcher to stop the job
                job_wrapper = JobWrapper(job, self, use_persisted_destination=True)
                self.dispatcher.stop(job, job_wrapper)


class DefaultJobDispatcher:
    def __init__(self, app: MinimalManagerApp):
        self.app = app
        self.job_runners = self.app.job_config.get_job_runner_plugins(self.app.config.server_name)
        # Once plugins are loaded, all job destinations that were created from
        # URLs can have their URL params converted to the destination's param
        # dict by the plugin.
        self.app.job_config.convert_legacy_destinations(self.job_runners)
        log.debug(f"Loaded job runners plugins: {':'.join(self.job_runners.keys())}")

    def start(self):
        for runner in self.job_runners.values():
            runner.start()

    def url_to_destination(self, url: str):
        """This is used by the runner mapper (a.k.a. dynamic runner) and
        recovery methods to have runners convert URLs to destinations.

        New-style runner plugin IDs must match the URL's scheme for this to work.
        """
        runner_name = url.split(":", 1)[0]
        try:
            return self.job_runners[runner_name].url_to_destination(url)
        except Exception:
            log.exception(
                "Unable to convert legacy job runner URL '%s' to job destination, destination will be the '%s' runner with no params",
                url,
                runner_name,
            )
            return JobDestination(runner=runner_name)

    def get_job_runner(self, job_wrapper, get_task_runner=False):
        runner_name = job_wrapper.job_destination.runner
        try:
            runner = self.job_runners[runner_name]
        except KeyError:
            log.error(f"({job_wrapper.job_id}) Invalid job runner: {runner_name}")
            job_wrapper.fail(DEFAULT_JOB_RUNNER_FAILURE_MESSAGE)
            return None
        if get_task_runner and job_wrapper.can_split() and runner.runner_name != "PulsarJobRunner":
            return self.job_runners["tasks"]
        return runner

    def put(self, job_wrapper):
        runner = self.get_job_runner(job_wrapper, get_task_runner=True)
        if runner is None:
            # Something went wrong, we've already failed the job wrapper
            return
        if isinstance(job_wrapper, TaskWrapper):
            # DBTODO Refactor
            log.debug(f"({job_wrapper.job_id}) Dispatching task {job_wrapper.task_id} to task runner")
        else:
            log.debug(f"({job_wrapper.job_id}) Dispatching to {job_wrapper.job_destination.runner} runner")
        runner.put(job_wrapper)

    def stop(self, job, job_wrapper):
        """
        Stop the given job. The input variable job may be either a Job or a Task.
        """
        # The Job and Task classes have been modified so that their accessors
        # will return the appropriate value.
        # Note that Jobs and Tasks have runner_names, which are distinct from
        # the job_runner_name and task_runner_name.

        # The runner name is not set until the job has started.
        # If we're stopping a task, then the runner_name may be
        # None, in which case it hasn't been scheduled.
        if self.app.config.enable_celery_tasks and job.tool_id == "__DATA_FETCH__":
            from galaxy.celery import celery_app

            celery_app.control.revoke(job.job_runner_external_id)
        if (job_runner_name := job.get_job_runner_name()) is not None:
            runner_name = job_runner_name.split(":", 1)[0]
            log.debug(f"Stopping job {job_wrapper.get_id_tag()} in {runner_name} runner")
            try:
                if job.state != model.Job.states.NEW:
                    self.job_runners[runner_name].stop_job(job_wrapper)
            except KeyError:
                log.error(f"stop(): ({job_wrapper.get_id_tag()}) Invalid job runner: {runner_name}")
                # Job and output dataset states have already been updated, so nothing is done here.

    def recover(self, job, job_wrapper):
        runner_name = (job.job_runner_name.split(":", 1))[0]
        log.debug("recovering job %d in %s runner" % (job.id, runner_name))
        runner = self.get_job_runner(job_wrapper)
        try:
            runner.recover(job, job_wrapper)
        except ObjectNotFound:
            msg = "Could not recover job working directory after Galaxy restart"
            log.exception(f"recover(): ({job_wrapper.job_id}) {msg}")
            job_wrapper.fail(msg)

    def shutdown(self):
        failures = []
        for name, runner in self.job_runners.items():
            try:
                runner.shutdown()
            except Exception:
                failures.append(name)
                log.exception("Failed to shutdown runner %s", name)
        if failures:
            raise Exception(f"Failed to shutdown runners: {', '.join(failures)}")

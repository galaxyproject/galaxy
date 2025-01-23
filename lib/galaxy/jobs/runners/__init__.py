"""
Base classes for job runner plugins.
"""

import datetime
import os
import string
import subprocess
import sys
import threading
import time
import traceback
import uuid
from queue import (
    Empty,
    Queue,
)
from typing import (
    Any,
    Dict,
    Optional,
    TYPE_CHECKING,
    Union,
)

from sqlalchemy import select
from sqlalchemy.orm import object_session

import galaxy.jobs
from galaxy import model
from galaxy.exceptions import ConfigurationError
from galaxy.job_execution.output_collect import (
    default_exit_code_file,
    read_exit_code_from,
)
from galaxy.jobs.command_factory import build_command
from galaxy.jobs.runners.util import runner_states
from galaxy.jobs.runners.util.env import env_to_statement
from galaxy.jobs.runners.util.job_script import (
    job_script,
    write_script,
)
from galaxy.model.base import (
    check_database_connection,
    transaction,
)
from galaxy.tool_util.deps.dependencies import (
    JobInfo,
    ToolInfo,
)
from galaxy.tool_util.output_checker import DETECTED_JOB_STATE
from galaxy.util import (
    asbool,
    DATABASE_MAX_STRING_SIZE,
    ExecutionTimer,
    in_directory,
    ParamsWithSpecs,
    shrink_stream_by_size,
    unicodify,
    UNKNOWN,
)
from galaxy.util.custom_logging import get_logger
from galaxy.util.monitors import Monitors
from .state_handler_factory import build_state_handlers

if TYPE_CHECKING:
    from galaxy.app import GalaxyManagerApplication
    from galaxy.jobs import (
        JobDestination,
        JobWrapper,
        MinimalJobWrapper,
    )

log = get_logger(__name__)

STOP_SIGNAL = object()


JOB_RUNNER_PARAMETER_UNKNOWN_MESSAGE = "Invalid job runner parameter for this plugin: %s"
JOB_RUNNER_PARAMETER_MAP_PROBLEM_MESSAGE = (
    "Job runner parameter '%s' value '%s' could not be converted to the correct type"
)
JOB_RUNNER_PARAMETER_VALIDATION_FAILED_MESSAGE = "Job runner parameter %s failed validation"

GALAXY_LIB_ADJUST_TEMPLATE = """GALAXY_LIB="%s"; if [ "$GALAXY_LIB" != "None" ]; then if [ -n "$PYTHONPATH" ]; then PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"; else PYTHONPATH="$GALAXY_LIB"; fi; export PYTHONPATH; fi;"""
GALAXY_VENV_TEMPLATE = """GALAXY_VIRTUAL_ENV="%s"; if [ "$GALAXY_VIRTUAL_ENV" != "None" -a -z "$VIRTUAL_ENV" -a -f "$GALAXY_VIRTUAL_ENV/bin/activate" ]; then . "$GALAXY_VIRTUAL_ENV/bin/activate"; fi;"""


class RunnerParams(ParamsWithSpecs):
    def _param_unknown_error(self, name):
        raise Exception(JOB_RUNNER_PARAMETER_UNKNOWN_MESSAGE % name)

    def _param_map_error(self, name, value):
        raise Exception(JOB_RUNNER_PARAMETER_MAP_PROBLEM_MESSAGE % (name, value))

    def _param_vaildation_error(self, name, value):
        raise Exception(JOB_RUNNER_PARAMETER_VALIDATION_FAILED_MESSAGE % name)


class BaseJobRunner:
    runner_name = "BaseJobRunner"

    start_methods = ["_init_monitor_thread", "_init_worker_threads"]
    DEFAULT_SPECS = dict(recheck_missing_job_retries=dict(map=int, valid=lambda x: int(x) >= 0, default=0))

    def __init__(self, app: "GalaxyManagerApplication", nworkers: int, **kwargs):
        """Start the job runner"""
        self.app = app
        self.redact_email_in_job_name = self.app.config.redact_email_in_job_name
        self.sa_session = app.model.context
        self.nworkers = nworkers
        runner_param_specs = self.DEFAULT_SPECS.copy()
        if "runner_param_specs" in kwargs:
            runner_param_specs.update(kwargs.pop("runner_param_specs"))
        if kwargs:
            log.debug("Loading %s with params: %s", self.runner_name, kwargs)
        self.runner_params = RunnerParams(specs=runner_param_specs, params=kwargs)
        self.runner_state_handlers = build_state_handlers()
        self._should_stop = False

    def start(self):
        for start_method in self.start_methods:
            getattr(self, start_method, lambda: None)()

    def _init_worker_threads(self):
        """Start ``nworkers`` worker threads."""
        self.work_queue = Queue()
        self.work_threads = []
        log.debug(f"Starting {self.nworkers} {self.runner_name} workers")
        for i in range(self.nworkers):
            worker = threading.Thread(name=f"{self.runner_name}.work_thread-{i}", target=self.run_next)
            worker.daemon = True
            worker.start()
            self.work_threads.append(worker)

    def _alive_worker_threads(self, cycle=False):
        # yield endlessly as long as there are alive threads if cycle is True
        alive = True
        while alive:
            alive = False
            for thread in self.work_threads:
                if thread.is_alive():
                    if cycle:
                        alive = True
                    yield thread

    def run_next(self):
        """Run the next item in the work queue (a job waiting to run)"""
        while self._should_stop is False:
            with self.app.model.session():  # Create a Session instance and ensure it's closed.
                try:
                    (method, arg) = self.work_queue.get(timeout=1)
                except Empty:
                    continue
                if method is STOP_SIGNAL:
                    return
                # id and name are collected first so that the call of method() is the last exception.
                try:
                    if isinstance(arg, AsynchronousJobState):
                        job_id = arg.job_wrapper.get_id_tag()
                    else:
                        # arg should be a JobWrapper/TaskWrapper
                        job_id = arg.get_id_tag()
                except Exception:
                    job_id = UNKNOWN
                try:
                    name = method.__name__
                except Exception:
                    name = UNKNOWN

                # Ensure a Job object belongs to a session
                self._ensure_db_session(arg)

                try:
                    action_str = f"galaxy.jobs.runners.{self.__class__.__name__.lower()}.{name}"
                    action_timer = self.app.execution_timer_factory.get_timer(
                        f"internals.{action_str}", f"job runner action {action_str} for job ${{job_id}} executed"
                    )
                    method(arg)
                    log.trace(action_timer.to_str(job_id=job_id))
                except Exception:
                    log.exception(f"({job_id}) Unhandled exception calling {name}")
                    if not isinstance(arg, JobState):
                        job_state = JobState(job_wrapper=arg, job_destination={})
                    else:
                        job_state = arg
                    if method != self.fail_job:
                        # Prevent fail_job cycle in the work_queue
                        self.work_queue.put((self.fail_job, job_state))

    def _ensure_db_session(self, arg: Union["JobWrapper", "JobState"]) -> None:
        """Ensure Job object belongs to current session."""
        try:
            job_wrapper = arg.job_wrapper  # type: ignore[union-attr]
        except AttributeError:
            job_wrapper = arg

        if job_wrapper._job_io:
            job = job_wrapper._job_io.job
            if object_session(job) is None:
                self.app.model.session().add(job)

    # Causes a runner's `queue_job` method to be called from a worker thread
    def put(self, job_wrapper: "MinimalJobWrapper"):
        """Add a job to the queue (by job identifier), indicate that the job is ready to run."""
        put_timer = ExecutionTimer()
        try:
            queue_job = job_wrapper.enqueue()
        except Exception as e:
            queue_job = False
            # Required for exceptions thrown by object store incompatibility.
            # tested by test/integration/objectstore/test_private_handling.py
            message = e.client_message if hasattr(e, "client_message") else str(e)
            job_wrapper.fail(message, exception=e)
            log.debug(f"Job [{job_wrapper.job_id}] failed to queue {put_timer}")
            return
        if queue_job:
            self.mark_as_queued(job_wrapper)
            log.debug(f"Job [{job_wrapper.job_id}] queued {put_timer}")

    def mark_as_queued(self, job_wrapper: "MinimalJobWrapper"):
        self.work_queue.put((self.queue_job, job_wrapper))

    def shutdown(self):
        """Attempts to gracefully shut down the worker threads"""
        log.info("%s: Sending stop signal to %s job worker threads", self.runner_name, len(self.work_threads))
        self._should_stop = True
        for _ in range(len(self.work_threads)):
            self.work_queue.put((STOP_SIGNAL, None))

        if (join_timeout := self.app.config.monitor_thread_join_timeout) > 0:
            log.info("Waiting up to %d seconds for job worker threads to shutdown...", join_timeout)
            start = time.time()
            # NOTE: threads that have already joined by now are not going to be logged
            for thread in self._alive_worker_threads(cycle=True):
                if time.time() > (start + join_timeout):
                    break
                try:
                    thread.join(2)
                except Exception:
                    log.exception("Caught exception attempting to shutdown job worker thread %s:", thread.name)
                if not thread.is_alive():
                    log.debug("Job worker thread terminated: %s", thread.name)
            else:
                log.info("All job worker threads shutdown cleanly")
                return

            for thread in self._alive_worker_threads():
                try:
                    frame = sys._current_frames()[thread.ident]
                except KeyError:
                    # thread is now stopped
                    continue
                log.warning(
                    "Timed out waiting for job worker thread %s to terminate, shutdown will be unclean! Thread "
                    "stack is:\n%s",
                    thread.name,
                    "".join(traceback.format_stack(frame)),
                )

    # Most runners should override the legacy URL handler methods and destination param method
    def url_to_destination(self, url: str):
        """
        Convert a legacy URL to a JobDestination.

        Job runner URLs are deprecated, JobDestinations should be used instead.
        This base class method converts from a URL to a very basic
        JobDestination without destination params.
        """
        return galaxy.jobs.JobDestination(runner=url.split(":")[0])

    def parse_destination_params(self, params: Dict[str, Any]):
        """Parse the JobDestination ``params`` dict and return the runner's native representation of those params."""
        raise NotImplementedError()

    def prepare_job(
        self,
        job_wrapper: "MinimalJobWrapper",
        include_metadata: bool = False,
        include_work_dir_outputs: bool = True,
        modify_command_for_container: bool = True,
        stream_stdout_stderr: bool = False,
    ):
        """Some sanity checks that all runners' queue_job() methods are likely to want to do"""
        job_id = job_wrapper.get_id_tag()
        job_state = job_wrapper.get_state()
        job_wrapper.runner_command_line = None

        # Make sure the job hasn't been deleted
        if job_state == model.Job.states.DELETED:
            log.debug(f"({job_id}) Job deleted by user before it entered the {self.runner_name} queue")
            if self.app.config.cleanup_job in ("always", "onsuccess"):
                job_wrapper.cleanup()
            return False
        elif job_state != model.Job.states.QUEUED:
            log.info(f"({job_id}) Job is in state {job_state}, skipping execution")
            # cleanup may not be safe in all states
            return False

        # Prepare the job
        try:
            job_wrapper.prepare()
            job_wrapper.runner_command_line = self.build_command_line(
                job_wrapper,
                include_metadata=include_metadata,
                include_work_dir_outputs=include_work_dir_outputs,
                modify_command_for_container=modify_command_for_container,
                stream_stdout_stderr=stream_stdout_stderr,
            )
        except Exception as e:
            log.exception("(%s) Failure preparing job", job_id)
            job_wrapper.fail(unicodify(e), exception=True)
            return False

        if not job_wrapper.runner_command_line:
            job_wrapper.finish("", "")
            return False

        return True

    # Runners must override the job handling methods
    def queue_job(self, job_wrapper: "MinimalJobWrapper") -> None:
        raise NotImplementedError()

    def stop_job(self, job_wrapper):
        raise NotImplementedError()

    def recover(self, job, job_wrapper):
        raise NotImplementedError()

    def build_command_line(
        self,
        job_wrapper: "MinimalJobWrapper",
        include_metadata: bool = False,
        include_work_dir_outputs: bool = True,
        modify_command_for_container: bool = True,
        stream_stdout_stderr=False,
    ):
        container = self._find_container(job_wrapper)
        if not container and job_wrapper.requires_containerization:
            raise Exception("Failed to find a container when required, contact Galaxy admin.")
        return build_command(
            self,
            job_wrapper,
            include_metadata=include_metadata,
            include_work_dir_outputs=include_work_dir_outputs,
            modify_command_for_container=modify_command_for_container,
            container=container,
            stream_stdout_stderr=stream_stdout_stderr,
        )

    def get_work_dir_outputs(
        self,
        job_wrapper: "MinimalJobWrapper",
        job_working_directory: Optional[str] = None,
        tool_working_directory: Optional[str] = None,
    ):
        """
        Returns list of pairs (source_file, destination) describing path
        to work_dir output file and ultimate destination.
        """
        if tool_working_directory is not None and job_working_directory is not None:
            raise Exception(
                "get_work_dir_outputs called with both a job and tool working directory, only one may be specified"
            )

        if tool_working_directory is None:
            if not job_working_directory:
                job_working_directory = os.path.abspath(job_wrapper.working_directory)
                assert job_working_directory
            tool_working_directory = os.path.join(job_working_directory, "working")

        # Set up dict of dataset id --> output path; output path can be real or
        # false depending on outputs_to_working_directory
        output_paths = {}
        for dataset_path in job_wrapper.job_io.get_output_fnames():
            path = dataset_path.real_path
            if asbool(job_wrapper.get_destination_configuration("outputs_to_working_directory", False)):
                path = dataset_path.false_path
            output_paths[dataset_path.dataset_id] = path

        output_pairs = []
        # Walk job's output associations to find and use from_work_dir attributes.
        job = job_wrapper.get_job()
        job_tool = job_wrapper.tool
        for joda, dataset in self._walk_dataset_outputs(job):
            if joda and job_tool:
                if dataset.dataset.purged:
                    log.info(
                        "Output dataset %s for job %s purged before job completed, skipping output collection.",
                        joda.name,
                        job.id,
                    )
                    continue
                hda_tool_output = job_tool.find_output_def(joda.name)
                if hda_tool_output and hda_tool_output.from_work_dir:
                    # Copy from working dir to HDA.
                    # TODO: move instead of copy to save time?
                    source_file = os.path.join(tool_working_directory, hda_tool_output.from_work_dir)
                    destination = job_wrapper.get_output_destination(output_paths[dataset.dataset_id])
                    if in_directory(source_file, tool_working_directory):
                        output_pairs.append((source_file, destination))
                    else:
                        # Security violation.
                        log.exception(
                            "from_work_dir specified a location not in the working directory: %s, %s",
                            source_file,
                            job_wrapper.working_directory,
                        )
        return output_pairs

    def _walk_dataset_outputs(self, job: model.Job):
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            for dataset in (
                dataset_assoc.dataset.dataset.history_associations + dataset_assoc.dataset.dataset.library_associations
            ):
                if isinstance(dataset, self.app.model.HistoryDatasetAssociation):
                    stmt = (
                        select(self.app.model.JobToOutputDatasetAssociation)
                        .filter_by(job=job, dataset=dataset)
                        .limit(1)
                    )
                    joda = self.sa_session.scalars(stmt).first()
                    yield (joda, dataset)
        # TODO: why is this not just something easy like:
        # for dataset_assoc in job.output_datasets + job.output_library_datasets:
        #      yield (dataset_assoc, dataset_assoc.dataset)
        #  I don't understand the reworking it backwards.  -John

    def _verify_celery_config(self):
        if not self.app.config.enable_celery_tasks:
            raise ConfigurationError("Can't request celery metadata without enabling celery tasks")
        celery_conf = self.app.config.celery_conf
        if not celery_conf and not celery_conf["result_backend"]:
            raise ConfigurationError(
                "Celery backend not set. Please set `result_backend` on the `celery_conf` config option."
            )

    def _handle_metadata_externally(self, job_wrapper: "MinimalJobWrapper", resolve_requirements: bool = False):
        """
        Set metadata externally. Used by the Pulsar job runner where this
        shouldn't be attached to command line to execute.
        """
        # run the metadata setting script here
        # this is terminate-able when output dataset/job is deleted
        # so that long running set_meta()s can be canceled without having to reboot the server
        if job_wrapper.get_state() not in [model.Job.states.ERROR, model.Job.states.DELETED]:
            external_metadata_script = job_wrapper.setup_external_metadata(
                output_fnames=job_wrapper.job_io.get_output_fnames(),
                set_extension=True,
                tmp_dir=job_wrapper.working_directory,
                # We don't want to overwrite metadata that was copied over in init_meta(), as per established behavior
                kwds={"overwrite": False},
            )
            metadata_strategy = job_wrapper.metadata_strategy
            if "celery" in metadata_strategy:
                self._verify_celery_config()
                from galaxy.celery.tasks import set_job_metadata

                # We're synchronously waiting for a task here. This means we have to have a result backend.
                # That is bad practice and also means this can never become part of another task.
                try:
                    set_job_metadata.delay(
                        tool_job_working_directory=job_wrapper.working_directory,
                        job_id=job_wrapper.job_id,
                        extended_metadata_collection="extended" in metadata_strategy,
                    ).get()
                except Exception:
                    log.exception("Metadata task failed")
                    return
            else:
                lib_adjust = GALAXY_LIB_ADJUST_TEMPLATE % job_wrapper.galaxy_lib_dir
                venv = GALAXY_VENV_TEMPLATE % job_wrapper.galaxy_virtual_env
                external_metadata_script = f"{lib_adjust} {venv} {external_metadata_script}"
                if resolve_requirements:
                    dependency_shell_commands = (
                        self.app.datatypes_registry.set_external_metadata_tool.build_dependency_shell_commands(
                            job_directory=job_wrapper.working_directory
                        )
                    )
                    if dependency_shell_commands:
                        if isinstance(dependency_shell_commands, list):
                            dependency_shell_commands = "&&".join(dependency_shell_commands)
                        external_metadata_script = f"{dependency_shell_commands}&&{external_metadata_script}"
                log.debug(
                    "executing external set_meta script for job %d: %s", job_wrapper.job_id, external_metadata_script
                )
                subprocess.call(
                    args=external_metadata_script,
                    shell=True,
                    cwd=job_wrapper.working_directory,
                    env=os.environ,
                    preexec_fn=os.setpgrp,
                )
            log.debug("execution of external set_meta for job %d finished", job_wrapper.job_id)

    def get_job_file(self, job_wrapper: "MinimalJobWrapper", **kwds) -> str:
        job_metrics = job_wrapper.app.job_metrics
        job_instrumenter = job_metrics.job_instrumenters[job_wrapper.job_destination.id]

        env_setup_commands = kwds.get("env_setup_commands", [])
        env_setup_commands.append(job_wrapper.get_env_setup_clause() or "")
        destination = job_wrapper.job_destination
        envs = destination.get("env", [])
        envs.extend(job_wrapper.environment_variables)
        for env in envs:
            env_setup_commands.append(env_to_statement(env))
        command_line = job_wrapper.runner_command_line
        tmp_dir_creation_statement = job_wrapper.tmp_dir_creation_statement
        assert job_wrapper.tool
        options = dict(
            tmp_dir_creation_statement=tmp_dir_creation_statement,
            job_instrumenter=job_instrumenter,
            galaxy_lib=job_wrapper.galaxy_lib_dir,
            galaxy_virtual_env=job_wrapper.galaxy_virtual_env,
            env_setup_commands=env_setup_commands,
            working_directory=os.path.abspath(job_wrapper.working_directory),
            command=command_line,
            shell=job_wrapper.shell,
            preserve_python_environment=job_wrapper.tool.requires_galaxy_python_environment,
        )
        # Additional logging to enable if debugging from_work_dir handling, metadata
        # commands, etc... (or just peak in the job script.)
        job_id = job_wrapper.job_id
        log.debug(f"({job_id}) command is: {command_line}")
        options.update(**kwds)
        return job_script(**options)

    def write_executable_script(self, path: str, contents: str) -> None:
        write_script(path, contents)

    def _find_container(
        self,
        job_wrapper: "MinimalJobWrapper",
        compute_working_directory: Optional[str] = None,
        compute_tool_directory: Optional[str] = None,
        compute_job_directory: Optional[str] = None,
        compute_tmp_directory: Optional[str] = None,
    ):
        job_directory_type = "galaxy" if compute_working_directory is None else "pulsar"
        if not compute_working_directory:
            compute_working_directory = job_wrapper.tool_working_directory

        if not compute_job_directory:
            compute_job_directory = job_wrapper.working_directory

        tool = job_wrapper.tool
        assert tool
        if not compute_tool_directory:
            compute_tool_directory = str(tool.tool_dir) if tool.tool_dir is not None else None

        if not compute_tmp_directory:
            compute_tmp_directory = job_wrapper.tmp_directory()

        guest_ports = job_wrapper.guest_ports
        tool_info = ToolInfo(
            tool.containers,
            tool.requirements,
            tool.requires_galaxy_python_environment,
            tool.docker_env_pass_through,
            guest_ports=guest_ports,
            tool_id=tool.id,
            tool_version=tool.version,
            profile=tool.profile,
        )
        job_info = JobInfo(
            working_directory=compute_working_directory,
            tool_directory=compute_tool_directory,
            job_directory=compute_job_directory,
            tmp_directory=compute_tmp_directory,
            home_directory=job_wrapper.home_directory(),
            job_directory_type=job_directory_type,
        )

        destination_info = job_wrapper.job_destination.params
        container = self.app.container_finder.find_container(tool_info, destination_info, job_info)
        if container:
            job_wrapper.set_container(container)
        return container

    def _handle_runner_state(self, runner_state, job_state: "JobState"):
        try:
            for handler in self.runner_state_handlers.get(runner_state, []):
                handler(self.app, self, job_state)
                if job_state.runner_state_handled:
                    break
        except Exception:
            log.exception("Caught exception in runner state handler")

    def fail_job(self, job_state: "JobState", exception=False, message="Job failed", full_status=None):
        job = job_state.job_wrapper.get_job()
        if getattr(job_state, "stop_job", True) and job.state != model.Job.states.NEW:
            self.stop_job(job_state.job_wrapper)
        job_state.job_wrapper.reclaim_ownership()
        self._handle_runner_state("failure", job_state)
        # Not convinced this is the best way to indicate this state, but
        # something necessary
        if not job_state.runner_state_handled:
            # full_status currently only passed in pulsar runner,
            # but might be useful for other runners in the future.
            full_status = full_status or {}
            tool_stdout = full_status.get("stdout")
            tool_stderr = full_status.get("stderr")
            fail_message = getattr(job_state, "fail_message", message)
            job_state.job_wrapper.fail(
                fail_message, tool_stdout=tool_stdout, tool_stderr=tool_stderr, exception=exception
            )

    def mark_as_resubmitted(self, job_state: "JobState", info: Optional[str] = None):
        job_state.job_wrapper.mark_as_resubmitted(info=info)
        if not self.app.config.track_jobs_in_database:
            job_state.job_wrapper.change_state(model.Job.states.QUEUED)
            self.app.job_manager.job_handler.dispatcher.put(job_state.job_wrapper)

    def _job_io_for_db(self, stream):
        return shrink_stream_by_size(
            stream, DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True
        )

    def _finish_or_resubmit_job(self, job_state: "JobState", job_stdout, job_stderr, job_id=None, external_job_id=None):
        job_wrapper = job_state.job_wrapper
        try:
            job = job_state.job_wrapper.get_job()
            if job_id is None:
                job_id = job.get_id_tag()
            if external_job_id is None:
                external_job_id = job.get_job_runner_external_id()
            exit_code = job_state.read_exit_code()

            outputs_directory = os.path.join(job_wrapper.working_directory, "outputs")
            if not os.path.exists(outputs_directory):
                outputs_directory = job_wrapper.working_directory

            tool_stdout_path = os.path.join(outputs_directory, "tool_stdout")
            tool_stderr_path = os.path.join(outputs_directory, "tool_stderr")
            try:
                with open(tool_stdout_path, "rb") as stdout_file:
                    tool_stdout = self._job_io_for_db(stdout_file)
                with open(tool_stderr_path, "rb") as stderr_file:
                    tool_stderr = self._job_io_for_db(stderr_file)
            except FileNotFoundError:
                if job.state in (model.Job.states.DELETING, model.Job.states.DELETED):
                    # We killed the job, so we may not even have the tool stdout / tool stderr
                    tool_stdout = ""
                    tool_stderr = "Job cancelled"
                else:
                    # Should we instead just move on ?
                    # In the end the only consequence here is that we won't be able to determine
                    # if the job failed for known tool reasons (check_tool_output).
                    # OTOH I don't know if this can even be reached
                    # Deal with it if we ever get reports about this.
                    raise

            check_output_detected_state = job_wrapper.check_tool_output(
                tool_stdout,
                tool_stderr,
                tool_exit_code=exit_code,
                job=job,
                job_stdout=job_stdout,
                job_stderr=job_stderr,
            )
            job_ok = check_output_detected_state == DETECTED_JOB_STATE.OK

            # clean up the job files
            cleanup_job = job_state.job_wrapper.cleanup_job
            if cleanup_job == "always" or (job_ok and cleanup_job == "onsuccess"):
                job_state.cleanup()

            # Flush with streams...
            self.sa_session.add(job)
            with transaction(self.sa_session):
                self.sa_session.commit()

            if not job_ok:
                job_runner_state = JobState.runner_states.TOOL_DETECT_ERROR
                if check_output_detected_state == DETECTED_JOB_STATE.OUT_OF_MEMORY_ERROR:
                    job_runner_state = JobState.runner_states.MEMORY_LIMIT_REACHED
                job_state.runner_state = job_runner_state
                self._handle_runner_state("failure", job_state)
                # Was resubmitted or something - I think we are done with it.
                if job_state.runner_state_handled:
                    return

            job_wrapper.finish(
                tool_stdout,
                tool_stderr,
                exit_code,
                check_output_detected_state=check_output_detected_state,
                job_stdout=job_stdout,
                job_stderr=job_stderr,
            )
        except Exception:
            log.exception(f"({job_id or ''}/{external_job_id or ''}) Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)


class JobState:
    """
    Encapsulate state of jobs.
    """

    runner_states = runner_states

    def __init__(self, job_wrapper: "JobWrapper", job_destination: "JobDestination"):
        self.runner_state_handled = False
        self.job_wrapper = job_wrapper
        self.job_destination = job_destination
        self.runner_state = None
        self.redact_email_in_job_name = True
        self._exit_code_file = None
        if self.job_wrapper:
            self.redact_email_in_job_name = self.job_wrapper.app.config.redact_email_in_job_name

        self.cleanup_file_attributes = ["job_file", "output_file", "error_file", "exit_code_file"]

    @property
    def exit_code_file(self) -> str:
        return self._exit_code_file or default_exit_code_file(
            self.job_wrapper.working_directory, self.job_wrapper.get_id_tag()
        )

    def set_defaults(self, files_dir):
        if self.job_wrapper is not None:
            id_tag = self.job_wrapper.get_id_tag()
            if files_dir is not None:
                self.job_file = JobState.default_job_file(files_dir, id_tag)
                self.output_file = os.path.join(files_dir, f"galaxy_{id_tag}.o")
                self.error_file = os.path.join(files_dir, f"galaxy_{id_tag}.e")
            job_name = f"g{id_tag}"
            if self.job_wrapper.tool.old_id:
                job_name += f"_{self.job_wrapper.tool.old_id}"
            if not self.redact_email_in_job_name and self.job_wrapper.user:
                job_name += f"_{self.job_wrapper.user}"
            self.job_name = "".join(x if x in (f"{string.ascii_letters + string.digits}_") else "_" for x in job_name)

    @staticmethod
    def default_job_file(files_dir, id_tag):
        return os.path.join(files_dir, f"galaxy_{id_tag}.sh")

    def read_exit_code(self):
        return read_exit_code_from(self.exit_code_file, self.job_wrapper.get_id_tag())

    def cleanup(self):
        for file in [getattr(self, a) for a in self.cleanup_file_attributes if hasattr(self, a)]:
            try:
                os.unlink(file)
            except Exception as e:
                # TODO: Move this prefix stuff to a method so we don't have dispatch on attributes we may or may
                # not have.
                if not hasattr(self, "job_id"):
                    prefix = f"({self.job_wrapper.get_id_tag()})"
                else:
                    prefix = f"({self.job_wrapper.get_id_tag()}/{self.job_id})"
                log.debug(f"{prefix} Unable to cleanup {file}: {unicodify(e)}")


class AsynchronousJobState(JobState):
    """
    Encapsulate the state of an asynchronous job, this should be subclassed as
    needed for various job runners to capture additional information needed
    to communicate with distributed resource manager.
    """

    def __init__(
        self,
        files_dir=None,
        job_wrapper=None,
        job_id=None,
        job_file=None,
        output_file=None,
        error_file=None,
        exit_code_file=None,
        job_name=None,
        job_destination=None,
    ):
        super().__init__(job_wrapper, job_destination)
        self.old_state = None
        self._running = False
        self.check_count = 0
        self.start_time = None

        # job_id is the DRM's job id, not the Galaxy job id
        self.job_id = job_id

        self.job_file = job_file
        self.output_file = output_file
        self.error_file = error_file
        if exit_code_file:
            self._exit_code_file = exit_code_file
        self.job_name = job_name

        self.set_defaults(files_dir)

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, is_running):
        self._running = is_running
        # This will be invalid for job recovery
        if self.start_time is None:
            self.start_time = datetime.datetime.now()

    def check_limits(self, runtime=None):
        limit_state = None
        if self.job_wrapper.has_limits():
            self.check_count += 1
            if self.running and (self.check_count % 20 == 0):
                if runtime is None:
                    runtime = datetime.datetime.now() - (self.start_time or datetime.datetime.now())
                self.check_count = 0
                limit_state = self.job_wrapper.check_limits(runtime=runtime)
        if limit_state is not None:
            # Set up the job for failure, but the runner will do the actual work
            self.runner_state, self.fail_message = limit_state
            self.stop_job = True
            return True
        return False

    def register_cleanup_file_attribute(self, attribute):
        if attribute not in self.cleanup_file_attributes:
            self.cleanup_file_attributes.append(attribute)


class AsynchronousJobRunner(BaseJobRunner, Monitors):
    """Parent class for any job runner that runs jobs asynchronously (e.g. via
    a distributed resource manager).  Provides general methods for having a
    thread to monitor the state of asynchronous jobs and submitting those jobs
    to the correct methods (queue, finish, cleanup) at appropriate times..
    """

    def __init__(self, app, nworkers, **kwargs):
        super().__init__(app, nworkers, **kwargs)
        # 'watched' and 'queue' are both used to keep track of jobs to watch.
        # 'queue' is used to add new watched jobs, and can be called from
        # any thread (usually by the 'queue_job' method). 'watched' must only
        # be modified by the monitor thread, which will move items from 'queue'
        # to 'watched' and then manage the watched jobs.
        self.watched = []
        self.monitor_queue = Queue()

    def _init_monitor_thread(self):
        name = f"{self.runner_name}.monitor_thread"
        super()._init_monitor_thread(name=name, target=self.monitor, start=True, config=self.app.config)

    def handle_stop(self):
        # DRMAA and SGE runners should override this and disconnect.
        pass

    def monitor(self):
        """
        Watches jobs currently in the monitor queue and deals with state
        changes (queued to running) and job completion.
        """
        while True:
            # Take any new watched jobs and put them on the monitor list
            try:
                while True:
                    async_job_state = self.monitor_queue.get_nowait()
                    if async_job_state is STOP_SIGNAL:
                        # TODO: This is where any cleanup would occur
                        self.handle_stop()
                        return
                    self.watched.append(async_job_state)
            except Empty:
                pass
            # Ideally we'd construct a sqlalchemy session now and pass it into `check_watched_items`
            # and have that be the only session being used. The next best thing is to scope
            # the session and discard it after each check_watched_item loop
            scoped_id = str(uuid.uuid4())
            self.app.model.set_request_id(scoped_id)
            # Iterate over the list of watched jobs and check state
            try:
                check_database_connection(self.sa_session)
                self.check_watched_items()
            except Exception:
                log.exception("Unhandled exception checking active jobs")
            finally:
                self.app.model.unset_request_id(scoped_id)
            # Sleep a bit before the next state check
            time.sleep(self.app.config.job_runner_monitor_sleep)

    def monitor_job(self, job_state):
        self.monitor_queue.put(job_state)

    def shutdown(self):
        """Attempts to gracefully shut down the monitor thread"""
        log.info(f"{self.runner_name}: Sending stop signal to monitor thread")
        self.monitor_queue.put(STOP_SIGNAL)
        # Call the parent's shutdown method to stop workers
        self.shutdown_monitor()
        super().shutdown()

    def check_watched_items(self):
        """
        This method is responsible for iterating over self.watched and handling
        state changes and updating self.watched with a new list of watched job
        states. Subclasses can opt to override this directly (as older job runners will
        initially) or just override check_watched_item and allow the list processing to
        reuse the logic here.
        """
        new_watched = []
        for async_job_state in self.watched:
            new_async_job_state = self.check_watched_item(async_job_state)
            if new_async_job_state:
                new_watched.append(new_async_job_state)
        self.watched = new_watched

    # Subclasses should implement this unless they override check_watched_items all together.
    def check_watched_item(self, job_state):
        raise NotImplementedError()

    def finish_job(self, job_state: AsynchronousJobState):
        """
        Get the output/error for a finished job, pass to `job_wrapper.finish`
        and cleanup all the job's temporary files.
        """
        galaxy_id_tag = job_state.job_wrapper.get_id_tag()
        external_job_id = job_state.job_id

        # To ensure that files below are readable, ownership must be reclaimed first
        job_state.job_wrapper.reclaim_ownership()

        # wait for the files to appear
        which_try = 0
        collect_output_success = True
        while which_try < self.app.config.retry_job_output_collection + 1:
            try:
                with open(job_state.output_file, "rb") as stdout_file, open(job_state.error_file, "rb") as stderr_file:
                    stdout = self._job_io_for_db(stdout_file)
                    stderr = self._job_io_for_db(stderr_file)
                break
            except Exception as e:
                if which_try == self.app.config.retry_job_output_collection:
                    stdout = ""
                    stderr = job_state.runner_states.JOB_OUTPUT_NOT_RETURNED_FROM_CLUSTER
                    log.error("(%s/%s) %s: %s", galaxy_id_tag, external_job_id, stderr, unicodify(e))
                    collect_output_success = False
                else:
                    time.sleep(1)
                which_try += 1

        if not collect_output_success:
            job_state.fail_message = stderr
            job_state.runner_state = job_state.runner_states.JOB_OUTPUT_NOT_RETURNED_FROM_CLUSTER
            self.mark_as_failed(job_state)
            return

        self._finish_or_resubmit_job(job_state, stdout, stderr, job_id=galaxy_id_tag, external_job_id=external_job_id)

    def mark_as_finished(self, job_state):
        self.work_queue.put((self.finish_job, job_state))

    def mark_as_failed(self, job_state):
        self.work_queue.put((self.fail_job, job_state))

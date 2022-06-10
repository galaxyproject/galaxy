import functools
import logging
import os

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.util import unicodify

CHRONOS_IMPORT_MSG = (
    "The Python 'chronos' package is required to use "
    "this feature, please install it or correct the "
    "following error:\nImportError {msg!s}"
)

try:
    import chronos

    chronos_exceptions = (
        chronos.ChronosAPIError,
        chronos.UnauthorizedError,
        chronos.MissingFieldError,
        chronos.OneOfViolationError,
    )
except ImportError as e:
    chronos = None
    CHRONOS_IMPORT_MSG.format(msg=unicodify(e))


__all__ = ("ChronosJobRunner",)
LOGGER = logging.getLogger(__name__)


class ChronosRunnerException(Exception):
    pass


def handle_exception_call(func):
    # Catch chronos exceptions. The latest version of chronos-python does
    # support a hierarchy over the exceptions.

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except chronos_exceptions as e:
            LOGGER.error(unicodify(e))

    return wrapper


def to_dict(segments, v):
    if len(segments) == 0:
        return v
    return {segments[0]: to_dict(segments[1:], v)}


def _write_logfile(logfile, msg):
    with open(logfile, "w") as fil:
        fil.write(msg)


def _parse_job_volumes_list(li):
    # Convert comma separated string to list
    volume_list = list(li.split(","))
    # Create the list with right mountpoint and permissions
    mountpoint_list = []
    # Convert each element to right format
    for i in volume_list:
        hpath, cpath, mode = i.split(":")
        mountpoint_list.append({"hostPath": hpath, "containerPath": cpath, "mode": mode})
    return mountpoint_list


def _add_galaxy_environment_variables(cpus, memory):
    # Set:
    # GALAXY_SLOTS: to docker_cpu
    # GALAXY_MEMORY_MB to docker_memory
    return [{"name": "GALAXY_SLOTS", "value": cpus}, {"name": "GALAXY_MEMORY_MB", "value": memory}]


class ChronosJobRunner(AsynchronousJobRunner):
    runner_name = "ChronosRunner"
    RUNNER_PARAM_SPEC_KEY = "runner_param_specs"
    JOB_NAME_PREFIX = "galaxy-chronos-"

    RUNNER_PARAM_SPEC = {
        "chronos": {
            "map": str,
        },
        "insecure": {
            "map": lambda x: x in ["true", "True", "TRUE"],
            "default": True,
        },
        "username": {
            "map": str,
        },
        "password": {
            "map": str,
        },
        "owner": {"map": str},
    }

    DESTINATION_PARAMS_SPEC = {
        "docker_cpu": {
            "default": 0.1,
            "map_name": "cpus",
            "map": float,
        },
        "docker_memory": {
            "default": 128,
            "map_name": "mem",
            "map": int,
        },
        "docker_disk": {
            "default": 256,
            "map_name": "disk",
            "map": int,
        },
        "volumes": {
            "default": None,
            "map_name": "container/volumes",
            "map": (lambda x: _parse_job_volumes_list(x) if x is not None else []),
        },
        "max_retries": {
            "default": 2,
            "map_name": "retries",
            "map": int,
        },
    }

    def __init__(self, app, nworkers, **kwargs):
        """Initialize this job runner and start the monitor thread"""
        assert chronos, CHRONOS_IMPORT_MSG
        if self.RUNNER_PARAM_SPEC_KEY not in kwargs:
            kwargs[self.RUNNER_PARAM_SPEC_KEY] = {}
        kwargs[self.RUNNER_PARAM_SPEC_KEY].update(self.RUNNER_PARAM_SPEC)
        super().__init__(app, nworkers, **kwargs)
        protocol = "http" if self.runner_params.get("insecure", True) else "https"
        self._chronos_client = chronos.connect(
            self.runner_params["chronos"],
            username=self.runner_params.get("username"),
            password=self.runner_params.get("password"),
            proto=protocol,
        )

    @handle_exception_call
    def queue_job(self, job_wrapper):
        LOGGER.debug(f"Starting queue_job for job {job_wrapper.get_id_tag()}")
        if not self.prepare_job(job_wrapper, include_metadata=False, modify_command_for_container=False):
            LOGGER.debug(f"Not ready {job_wrapper.get_id_tag()}")
            return
        job_destination = job_wrapper.job_destination
        chronos_job_spec = self._get_job_spec(job_wrapper)
        job_name = chronos_job_spec["name"]
        self._chronos_client.add(chronos_job_spec)
        ajs = AsynchronousJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper,
            job_id=job_name,
            job_destination=job_destination,
        )
        self.monitor_queue.put(ajs)

    @handle_exception_call
    def stop_job(self, job_wrapper):
        job_id = job_wrapper.get_id_tag()
        job_name = self.JOB_NAME_PREFIX + job_id
        job = self._retrieve_job(job_name)
        if job:
            msg = "Job {name!r} is terminated"
            self._chronos_client.delete(job_name)
            LOGGER.debug(msg.format(name=job_name))
        else:
            msg = "Job {name!r} not found. It cannot be terminated."
            LOGGER.error(msg.format(name=job_name))

    def recover(self, job, job_wrapper):
        msg = "(name!r/runner!r) is still in {state!s} state, adding to" " the runner monitor queue"
        job_id = job.get_job_runner_external_id()
        ajs = AsynchronousJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper,
            job_id=self.JOB_NAME_PREFIX + str(job_id),
            job_destination=job_wrapper.job_destination,
        )
        ajs.command_line = job.command_line
        if job.state in (model.Job.states.RUNNING, model.Job.states.STOPPED):
            LOGGER.debug(msg.format(name=job.id, runner=job.job_runner_external_id, state=job.state))
            ajs.old_state = model.Job.states.RUNNING
            ajs.running = True
            self.monitor_queue.put(ajs)
        elif job.state == model.Job.states.QUEUED:
            LOGGER.debug(msg.format(name=job.id, runner=job.job_runner_external_id, state="queued"))
            ajs.old_state = model.Job.states.QUEUED
            ajs.running = False
            self.monitor_queue.put(ajs)

    @handle_exception_call
    def check_watched_item(self, job_state):
        job_name = job_state.job_id
        job = self._retrieve_job(job_name)
        # TODO: how can stopped GxIT jobs be handled here?
        if job:
            succeeded = job["successCount"]
            errors = job["errorCount"]
            if succeeded > 0:
                return self._mark_as_successful(job_state)
            elif not succeeded and not errors:
                return self._mark_as_active(job_state)
            elif errors:
                max_retries = job["retries"]
                if max_retries == 0:
                    msg = "Job {name!r} failed. No retries performed."
                else:
                    msg = "Job {name!r} failed more than {retries!s} times."
                reason = msg.format(name=job_name, retries=str(max_retries))
                return self._mark_as_failed(job_state, reason)
        reason = f"Job {job_name!r} not found"
        return self._mark_as_failed(job_state, reason)

    def _mark_as_successful(self, job_state):
        msg = "Job {name!r} finished successfully"
        _write_logfile(job_state.output_file, msg.format(name=job_state.job_id))
        _write_logfile(job_state.error_file, "")
        job_state.running = False
        job_state.job_wrapper.change_state(model.Job.states.OK)
        self.mark_as_finished(job_state)
        return None

    def _mark_as_active(self, job_state):
        job_state.running = True
        job_state.job_wrapper.change_state(model.Job.states.RUNNING)
        return job_state

    def _mark_as_failed(self, job_state, reason):
        _write_logfile(job_state.error_file, reason)
        job_state.running = False
        job_state.stop_job = True
        job_state.job_wrapper.change_state(model.Job.states.ERROR)
        job_state.fail_message = reason
        self.mark_as_failed(job_state)
        return None

    @handle_exception_call
    def finish_job(self, job_state):
        super().finish_job(job_state)
        self._chronos_client.delete(job_state.job_id)

    def parse_destination_params(self, params):
        parsed_params = {}
        for k, spec in self.DESTINATION_PARAMS_SPEC.items():
            value = params.get(k, spec.get("default"))
            map_to = spec.get("map_name")
            mapper = spec.get("map")
            segments = map_to.split("/")
            parsed_params.update(to_dict(segments, mapper(value)))
        return parsed_params

    def write_command(self, job_wrapper):
        # Create command script instead passing it in the container
        # preventing wrong characters parsing.
        if not os.path.exists(job_wrapper.working_directory):
            LOGGER.error("No working directory found")

        path = f"{job_wrapper.working_directory}/chronos_{job_wrapper.get_id_tag()}.sh"
        mode = 0o755

        with open(path, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            f.write(job_wrapper.runner_command_line)
        os.chmod(path, mode)
        return path

    def _get_job_spec(self, job_wrapper):
        job_name = self.JOB_NAME_PREFIX + job_wrapper.get_id_tag()
        job_destination = job_wrapper.job_destination
        command_script_path = self.write_command(job_wrapper)
        template = {
            "async": False,
            # 'command': job_wrapper.runner_command_line,
            "command": f"$SHELL {command_script_path}",
            "owner": self.runner_params["owner"],
            "disabled": False,
            "schedule": "R1//PT1S",
            "name": job_name,
            # Add Galaxy environemnt variables to json
            "environmentVariables": _add_galaxy_environment_variables(
                job_destination.params.get("docker_cpu"), job_destination.params.get("docker_memory")
            ),
        }
        if not job_destination.params.get("docker_enabled"):
            raise ChronosRunnerException("ChronosJobRunner needs 'docker_enabled' to be set as True")
        destination_params = self.parse_destination_params(job_destination.params)
        template.update(destination_params)
        template["container"]["type"] = "DOCKER"
        template["container"]["image"] = self._find_container(job_wrapper).container_id
        # Fix the working directory inside the container
        template["container"]["parameters"] = [{"key": "workdir", "value": job_wrapper.working_directory}]
        return template

    def _retrieve_job(self, job_id):
        jobs = self._chronos_client.list()
        job = [x for x in jobs if x["name"] == job_id]
        if len(job) > 1:
            msg = f"Multiple jobs found with name {job_id!r}"
            LOGGER.error(msg)
            raise ChronosRunnerException(msg)
        return job[0] if job else None

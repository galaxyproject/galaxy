import functools
import hashlib
import logging
import os
import time

from queue import Empty
from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.util import smart_str, unicodify

BOTO3_IMPORT_MSG = (
    "The Python 'boto3' package is required to use "
    "this feature, please install it or correct the "
    "following error:\nImportError {msg!s}"
)

try:
    import boto3

except ImportError as e:
    boto3 = None
    BOTO3_IMPORT_MSG.format(msg=unicodify(e))


__all__ = ("AWSBatchJobRunner",)
LOGGER = logging.getLogger(__name__)

STOP_SIGNAL = object()


class AWSBatchRunnerException(Exception):
    pass


def handle_exception_call(func):
    # Catch boto3 exceptions. 

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            LOGGER.error(unicodify(e))

    return wrapper


def to_dict(segments, v):
    if len(segments) == 0:
        return v
    return {segments[0]: to_dict(segments[1:], v)}


def _write_logfile(logfile, msg):
    with open(logfile, "w") as fil:
        fil.write(msg)


def _add_galaxy_environment_variables(cpus, memory):
    # Set:
    # GALAXY_SLOTS: to docker_cpu
    # GALAXY_MEMORY_MB to docker_memory
    return [{"name": "GALAXY_SLOTS", "value": cpus}, {"name": "GALAXY_MEMORY_MB", "value": memory}]


class AWSBatchJobRunner(AsynchronousJobRunner):
    runner_name = "AWSBatchRunner"
    RUNNER_PARAM_SPEC_KEY = "runner_param_specs"
    JOB_NAME_PREFIX = "galaxy-"
    # AWS Batch queries up to 100 jobs at once.
    MAX_JOBS_PER_QUERY = 100

    RUNNER_PARAM_SPEC = {
        "aws_access_key_id": {
            "map": str,
        },
        "aws_secret_access_key": {
            "map": str,
        }
    }

    DESTINATION_PARAMS_SPEC = {
        "vcpu": {
            "default": 1.0,
            "map_name": "vcpu",
            "map": str,
        },
        "memory": {
            "default": 2048,
            "map_name": "memory",
            "map": str,
        },
        "job_queue": {
            "default": None,
            "map_name": "job_queue",
            "map": str,
        },
        "job_role_arn": {
            "default": None,
            "map_name": "job_role_arn",
            "map": str,
        },
        "efs_filesystem_id": {
            "default": None,
            "map_name": "efs_filesystem_id",
            "map": str,
        },
        "efs_mount_point": {
            "default": None,
            "map_name": "efs_mount_point",
            "map": str,
        },
        "fargate_version": {
            "default": None,
            "map_name": "fargate_version",
            "map": str,
        }
    }

    def __init__(self, app, nworkers, **kwargs):
        """Initialize this job runner and start the monitor thread"""
        assert boto3, BOTO3_IMPORT_MSG
        if self.RUNNER_PARAM_SPEC_KEY not in kwargs:
            kwargs[self.RUNNER_PARAM_SPEC_KEY] = {}
        kwargs[self.RUNNER_PARAM_SPEC_KEY].update(self.RUNNER_PARAM_SPEC)
        super().__init__(app, nworkers, **kwargs)
        session = boto3.Session(
            aws_access_key_id=self.runner_params.get('aws_access_key_id') or None,
            aws_secret_access_key=self.runner_params.get('aws_secret_access_key') or None
        )
        self._batch_client = session.client('batch')

    @handle_exception_call
    def queue_job(self, job_wrapper):
        LOGGER.debug(f"Starting queue_job for job {job_wrapper.get_id_tag()}")
        if not self.prepare_job(job_wrapper, include_metadata=False, modify_command_for_container=False):
            LOGGER.debug(f"Not ready {job_wrapper.get_id_tag()}")
            return

        job_destination = job_wrapper.job_destination
        if not job_destination.params.get("docker_enabled"):
            raise AWSBatchRunnerException("AWSBatchJobRunner needs 'docker_enabled' to be set as True")

        destination_params = self.parse_destination_params(job_destination.params)
        job_def = self._get_job_definition(job_wrapper, destination_params)
        if 'fargate_version' in destination_params:
            job_name, job_id = self._submit_fargate_job(job_def, job_wrapper, destination_params)
        else:
            job_name, job_id = self._submit_ec2_job(job_def, job_wrapper, destination_params)

        ajs = AsynchronousJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper,
            job_name=job_name,
            job_id=job_id,
            job_destination=job_destination,
        )
        self.monitor_queue.put(ajs)

    def _get_job_definition(self, job_wrapper, destination_params):
        tool_id = job_wrapper.tool.id
        tool_version = job_wrapper.tool.version
        h = hashlib.new("sha256")
        h.update(smart_str(tool_version))
        compute_type = 'fargate' if 'fargate_version' in destination_params else 'ec2'

        jd_name = f"galaxy_tool__{tool_id}__{h.hexdigest()}__{compute_type}"
        res = self._batch_client.describe_job_definitions(
            jobDefinitionName=jd_name,
            status="ACTIVE"
        )
        if not res['jobDefinitions']:
            docker_image = docker_image = self._find_container(job_wrapper).container_id
            # user_id = job_wrapper.user.id
            jd_arn = self._register_job_definition(jd_name, docker_image, destination_params)
        else:
            jd_arn = res['jobDefinitions'][0]['jobDefinitionArn']
        
        return jd_arn

    def _register_job_definition(self, jd_name, docker_image, destination_params):
        if 'fargate_version' in destination_params:
            return self._register_fargate_job_definition(jd_name, docker_image, destination_params)
        else:
            return self._register_ec2_job_definition(jd_name, docker_image, destination_params)

    def _register_fargate_job_definition(self, jd_name, docker_image, destination_params):
        res = self._batch_client.register_job_definition(
            jobDefinitionName=jd_name,
            type='container',
            platformCapabilities=['FARGATE'],
            containerProperties={
                'image': docker_image,
                'command': [
                    '/bin/sh',
                ],
                'jobRoleArn': destination_params.get('job_role_arn'),
                'executionRoleArn': destination_params.get('execute_role_arn', None) or destination_params.get('job_role_arn'),
                'volumes': [
                    {
                        'name': 'efs_whole',
                        'efsVolumeConfiguration': {
                            'fileSystemId': destination_params.get('efs_filesystem_id'),
                            'rootDirectory': '/',
                            'transitEncryption': 'ENABLED',
                            'authorizationConfig': {
                                'iam': 'ENABLED'
                            }
                        }
                    },
                ],
                'mountPoints': [
                    {
                        'containerPath': destination_params.get('efs_mount_point'),
                        'readOnly': False,
                        'sourceVolume': 'efs_whole'
                    },
                ],
                'resourceRequirements': [
                    {
                        'type': 'VCPU',
                        'value': destination_params.get('vcpu')
                    },
                    {
                        'type': 'MEMORY',
                        'value': destination_params.get('memory')
                    }
                ],
                'fargatePlatformConfiguration': {
                    'platformVersion': destination_params.get('fargate_version')
                }
            }
        )

        assert res['ResponseMetadata']['HTTPStatusCode'] == 200

        return res['jobDefinitionArn']


    def _register_ec2_job_definition(self, jd_name, docker_image, user_id, destination_params):
        return ''

    def _submit_fargate_job(self, job_def, job_wrapper, destination_params):
        job_name = self.JOB_NAME_PREFIX + job_wrapper.get_id_tag()
        command_script_path = self.write_command(job_wrapper)

        res = self._batch_client.submit_job(
            jobName=job_name,
            jobQueue=destination_params.get('job_queue'),
            jobDefinition=job_def,
            containerOverrides={
                'command': [
                    f'$SHELL {command_script_path}',
                ]
            }
        )

        assert res['ResponseMetadata']['HTTPStatusCode'] == 200

        return job_name, res['jobId']

    def _submit_ec2_job(self, job_def, job_wrapper, destination_params):
        pass

    @handle_exception_call
    def stop_job(self, job_state):
        job_id = job_state.job_id

        res = self._batch_client.describe_jobs
        self._batch_client.terminate_job(jobId=job_id, reason="Killed by Galaxy!")
        msg = "Job {name!r} is terminated"
        LOGGER.debug(msg.format(name=job_state.job_name))

    def recover(self, job, job_wrapper):
        msg = "(name!r/runner!r) is still in {state!s} state, adding to" " the runner monitor queue"
        job_id = job.get_job_runner_external_id()
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper)
        ajs.job_id = self.JOB_NAME_PREFIX + str(job_id)
        ajs.command_line = job.command_line
        ajs.job_wrapper = job_wrapper
        ajs.job_destination = job_wrapper.job_destination
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

    def fail_job(self, job_state, exception=False):
        if getattr(job_state, "stop_job", True):
            self.stop_job(job_state)
        job_state.job_wrapper.reclaim_ownership()
        self._handle_runner_state("failure", job_state)
        if not job_state.runner_state_handled:
            job_state.job_wrapper.fail(getattr(job_state, "fail_message", "Job failed"), exception=exception)
            self._finish_or_resubmit_job(job_state, "", job_state.fail_message, job_id=job_state.job_id)
            if job_state.job_wrapper.cleanup_job == "always":
                job_state.cleanup()

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
                    self.watched.append((async_job_state.job_id, async_job_state))
            except Empty:
                pass
            # Iterate over the list of watched jobs and check state
            try:
                self.check_watched_items()
            except Exception:
                LOGGER.exception("Unhandled exception checking active jobs")
            # Sleep a bit before the next state check
            time.sleep(self.app.config.job_runner_monitor_sleep)

    @handle_exception_call
    def check_watched_items(self):
        self.check_watched_items_by_batch(0, len(self.watched))

    def check_watched_items_by_batch(self, start: int, end: int):
        jobs = self.watched[start: self.MAX_JOBS_PER_QUERY]
        if not jobs:
            return

        jobs_dict = dict(jobs)

        res = self._batch_client.describe_jobs(jobs=list(jobs_dict.keys()))

        gotten = []
        for job in res['jobs']:
            status = job['status']
            job_id = job['jobId']
            gotten.append(job_id)
            job_state = jobs_dict[job_id]

            if status == 'SUCCEEDED':
                self.watched.remove((job_id, job_state))
                start -= 1
                self._mark_as_successful(job_state)
            elif status == 'FAILED':
                self.watched.remove((job_id, job_state))
                start -= 1
                reason = job['statusReason']
                self._mark_as_failed(job_state, reason)
            elif status in ('SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING', 'RUNNING'):
                self._mark_as_active(job_state)
            # TODO else?

        for job_id in set(jobs_dict.keys()) - set(gotten):
            job_state = jobs_dict[job_id]
            self.watched.remove((job_id, job_state))
            start -= 1
            reason = f"The track of Job {job_state} was lost for unknown reason!"
            self._mark_as_failed(job_state, reason)

        self.check_watched_items_by_batch(start+self.MAX_JOBS_PER_QUERY, end)

    def _mark_as_successful(self, job_state):
        msg = "Job {name!r} finished successfully"
        _write_logfile(job_state.output_file, msg.format(name=job_state.job_name))
        _write_logfile(job_state.error_file, "")
        job_state.running = False
        job_state.job_wrapper.change_state(model.Job.states.OK)
        self.mark_as_finished(job_state)

    def _mark_as_active(self, job_state):
        job_state.running = True
        job_state.job_wrapper.change_state(model.Job.states.RUNNING)

    def _mark_as_failed(self, job_state, reason):
        _write_logfile(job_state.error_file, reason)
        job_state.running = False
        job_state.stop_job = True
        job_state.job_wrapper.change_state(model.Job.states.ERROR)
        job_state.fail_message = reason
        self.mark_as_failed(job_state)

    # @handle_exception_call
    # def finish_job(self, job_state):
    #     super().finish_job(job_state)
    #     self._batch_client.delete(job_state.job_id)

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

        path = f"{job_wrapper.working_directory}/galaxy_{job_wrapper.get_id_tag()}.sh"
        mode = 0o755

        with open(path, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            f.write(job_wrapper.runner_command_line)
        os.chmod(path, mode)
        return path

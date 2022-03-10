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
            raise

    return wrapper


def to_dict(segments, v):
    if len(segments) == 0:
        return v
    return {segments[0]: to_dict(segments[1:], v)}


def _write_logfile(logfile, msg):
    with open(logfile, "w") as fil:
        fil.write(msg)


def _add_galaxy_environment_variables(vcpu, memory):
    # Set:
    # GALAXY_SLOTS, round 0.25 vpuc to 1.
    # GALAXY_MEMORY_MB
    return [
        {"name": "GALAXY_SLOTS", "value": str(int(max(vcpu, 1)))},
        {"name": "GALAXY_MEMORY_MB", "value": str(memory)}
    ]


def _add_resource_requirements(destination_params):
    rval = [
        {'type': 'VCPU', 'value': str(destination_params.get('vcpu'))},
        {'type': 'MEMORY', 'value': str(destination_params.get('memory'))}
    ]
    n_gpu = destination_params.get('gpu')
    if n_gpu:
        rval.append(
            {'type': 'GPU', 'value': str(n_gpu)}
        )
    return rval


class AWSBatchJobRunner(AsynchronousJobRunner):
    runner_name = "AWSBatchRunner"
    RUNNER_PARAM_SPEC_KEY = "runner_param_specs"
    JOB_NAME_PREFIX = "galaxy-"
    # AWS Batch queries up to 100 jobs at once.
    MAX_JOBS_PER_QUERY = 100
    # Higher minimum interval as jobs are queried in batches.
    MIN_QUERY_INTERVAL = 10

    RUNNER_PARAM_SPEC = {
        "aws_access_key_id": {
            "map": str
        },
        "aws_secret_access_key": {
            "map": str
        }
    }

    DESTINATION_PARAMS_SPEC = {
        "vcpu": {
            "default": 1.0,
            "map": (lambda x: int(float(x)) if int(float(x))==float(x) else float(x)),
        },
        "memory": {
            "default": 2048,
            "map": int,
        },
        "gpu": {
            "default": 0,
            "map": int,
        },
        "job_queue": {
            "default": None,
            "map": str,
            "required": True
        },
        "job_role_arn": {
            "default": None,
            "map": str,
            "required": True
        },
        "efs_filesystem_id": {
            "default": None,
            "map": str,
            "required": True
        },
        "efs_mount_point": {
            "default": None,
            "map": str,
            "required": True
        },
        "log_group_name": {
            "default": None,
            "map": str,
            "required": True
        },
        "execute_role_arn": {
            "default": '',
            "map": str,
        },
        "fargate_version": {
            "default": '',
            "map": str,
        },
        "auto_platform": {
            "default": False,
            "map": lambda x: x in ["true", "True", "TRUE"]
        }
    }

    FARGATE_VCPUS = [0.25, 0.5, 1, 2, 4]

    FARGATE_RESOURCES = {
        0.25: [512, 1024, 2048],
        0.5: [1024, 2048, 3072, 4096],
        1: [2048, 3072, 4096, 5120, 6144, 7168, 8192],
        2: [4096, 5120, 6144, 7168, 8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384],
        4: [8192, 9216, 10240, 11264, 12288, 13312, 14336, 15360, 16384, 17408, 18432,
            19456, 20480, 21504, 22528, 23552, 24576, 25600, 26624, 27648, 28672, 29696, 30720]
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
        self._logs_client = session.client('logs')

    @handle_exception_call
    def queue_job(self, job_wrapper):
        LOGGER.debug(f"Starting queue_job for job {job_wrapper.get_id_tag()}")
        if not self.prepare_job(job_wrapper, include_metadata=False, modify_command_for_container=False):
            LOGGER.debug(f"Not ready {job_wrapper.get_id_tag()}")
            return

        job_destination = job_wrapper.job_destination
        destination_params = self.parse_destination_params(job_destination.params)
        job_def = self._get_job_definition(job_wrapper, destination_params)
        job_name, job_id = self._submit_job(job_def, job_wrapper, destination_params)
        job_wrapper.set_external_id(job_id)
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
        h.update(smart_str(tool_id))
        h.update(smart_str(tool_version))
        for k, v in destination_params.items():
            h.update(smart_str(k+str(v)))
        queue_name = destination_params.get('job_queue').rsplit('/', 1)[-1]

        jd_name = f"galaxy_tool__{tool_id}__{h.hexdigest()}__{queue_name}"
        res = self._batch_client.describe_job_definitions(
            jobDefinitionName=jd_name,
            status="ACTIVE"
        )
        if not res['jobDefinitions']:
            docker_image = self._find_container(job_wrapper).container_id
            jd_arn = self._register_job_definition(jd_name, docker_image, destination_params)
        else:
            jd_arn = res['jobDefinitions'][0]['jobDefinitionArn']
            LOGGER.debug(f"Found existing job definition: {jd_name}.")
        
        return jd_arn

    def _register_job_definition(self, jd_name, docker_image, destination_params):
        LOGGER.debug(f"Registering a new job definition: {jd_name}.")
        platform = destination_params.get('platform')
        # TODO: support multi-node
        containerProperties = {
            'image': docker_image,
            'command': [
                '/bin/sh',
            ],
            'jobRoleArn': destination_params.get('job_role_arn'),
            'executionRoleArn': destination_params.get('execute_role_arn') or destination_params.get('job_role_arn'),
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
            'resourceRequirements': _add_resource_requirements(destination_params),
            'environment': _add_galaxy_environment_variables(
                destination_params.get('vcpu'),
                destination_params.get('memory')
            ),
            'logConfiguration': {
                'logDriver': 'awslogs'
            }
        }
        if platform == 'FARGATE':
            containerProperties.update(
                {
                    'networkConfiguration': {
                        'assignPublicIp': 'ENABLED'
                    },
                    'fargatePlatformConfiguration': {
                        'platformVersion': destination_params.get('fargate_version')
                    },
                    'logConfiguration': {
                        'logDriver': 'awslogs'
                    }
                }
            )

        res = self._batch_client.register_job_definition(
            jobDefinitionName=jd_name,
            type='container',
            platformCapabilities=[platform],
            containerProperties=containerProperties
        )

        assert res['ResponseMetadata']['HTTPStatusCode'] == 200
        return res['jobDefinitionArn']

    def _submit_job(self, job_def, job_wrapper, destination_params):
        job_name = self.JOB_NAME_PREFIX + job_wrapper.get_id_tag()
        command_script_path = self.write_command(job_wrapper)

        res = self._batch_client.submit_job(
            jobName=job_name,
            jobQueue=destination_params.get('job_queue'),
            jobDefinition=job_def,
            containerOverrides={
                'command': [
                    '/bin/bash',
                    f'{command_script_path}',
                ]
            }
        )

        assert res['ResponseMetadata']['HTTPStatusCode'] == 200
        return job_name, res['jobId']

    @handle_exception_call
    def stop_job(self, job_wrapper):
        job = job_wrapper.get_job()
        external_id = job.get_job_runner_external_id()
        job_name = self.JOB_NAME_PREFIX + job_wrapper.get_id_tag()

        self._batch_client.terminate_job(jobId=external_id, reason="Terminated by Galaxy!")
        msg = "Job {name!r} is terminated"
        LOGGER.debug(msg.format(name=job_name))

    def recover(self, job, job_wrapper):
        msg = "(name!r/runner!r) is still in {state!s} state, adding to" " the runner monitor queue"
        job_id = job.get_job_runner_external_id()
        job_name = self.JOB_NAME_PREFIX + job_wrapper.get_id_tag()
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper)
        ajs.job_id = str(job_id)
        ajs.job_name = job_name
        ajs.command_line = job.command_line
        ajs.job_wrapper = job_wrapper
        ajs.job_destination = job_wrapper.job_destination
        if job.state in (model.Job.states.RUNNING, model.Job.states.STOPPED):
            LOGGER.debug(msg.format(name=job.id, runner=job.job_runner_name, state=job.state))
            ajs.old_state = model.Job.states.RUNNING
            ajs.running = True
            self.monitor_queue.put(ajs)
        elif job.state == model.Job.states.QUEUED:
            LOGGER.debug(msg.format(name=job.id, runner=job.job_runner_name, state="queued"))
            ajs.old_state = model.Job.states.QUEUED
            ajs.running = False
            self.monitor_queue.put(ajs)

    def fail_job(self, job_state, exception=False):
        if getattr(job_state, "stop_job", True):
            self.stop_job(job_state.job_wrapper)
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
            time.sleep(max(self.app.config.job_runner_monitor_sleep, self.MIN_QUERY_INTERVAL))

    @handle_exception_call
    def check_watched_items(self):
        done = []
        self.check_watched_items_by_batch(0, len(self.watched), done)
        self.watched = [x for x in self.watched if x[0] not in done]

    def check_watched_items_by_batch(self, start: int, end: int, done: list):
        jobs = self.watched[start: start+self.MAX_JOBS_PER_QUERY]
        if not jobs:
            return

        jobs_dict = dict(jobs)

        res = self._batch_client.describe_jobs(jobs=list(jobs_dict.keys()))

        gotten = []
        for job in res['jobs']:
            status = job['status']
            job_id = job['jobId']
            log_stream_name = job['container']['logStreamName']
            gotten.append(job_id)
            job_state = jobs_dict[job_id]

            if status == 'SUCCEEDED':
                logs = self._get_log_events(job_state, log_stream_name)
                self._mark_as_successful(job_state, logs)
                done.append(job_id)
            elif status == 'FAILED':
                logs = self._get_log_events(job_state, log_stream_name)
                reason = job['statusReason']
                self._mark_as_failed(job_state, reason, logs)
                done.append(job_id)
            elif status in ('SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING', 'RUNNING'):
                self._mark_as_active(job_state)
            # TODO else?

        for job_id in set(jobs_dict.keys()) - set(gotten):
            job_state = jobs_dict[job_id]
            reason = f"The track of Job {job_state} was lost for unknown reason!"
            self._mark_as_failed(job_state, reason)
            done.append(job_id)

        self.check_watched_items_by_batch(start+self.MAX_JOBS_PER_QUERY, end, done)

    def _get_log_events(self, job_state, log_stream_name):
        log_group_name = job_state.job_destination.params.get('log_group_name')
        res = self._logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )
        messages = [e['message']for e in res['events']]
        return '\n'.join(messages)

    def _mark_as_successful(self, job_state, logs):
        _write_logfile(job_state.output_file, logs)
        _write_logfile(job_state.error_file, "")
        job_state.running = False
        job_state.job_wrapper.change_state(model.Job.states.OK)
        self.mark_as_finished(job_state)

    def _mark_as_active(self, job_state):
        job_state.running = True
        job_state.job_wrapper.change_state(model.Job.states.RUNNING)

    def _mark_as_failed(self, job_state, reason, logs):
        if logs:
            reason = '\n\n'.join((reason, logs))
        _write_logfile(job_state.error_file, reason)
        job_state.running = False
        job_state.stop_job = False
        job_state.job_wrapper.change_state(model.Job.states.ERROR)
        job_state.fail_message = reason
        self.mark_as_failed(job_state)

    def parse_destination_params(self, params):
        if not params.get("docker_enabled"):
            raise AWSBatchRunnerException("AWSBatchJobRunner needs 'docker_enabled' to be set as True!")

        check_required = []
        parsed_params = {}
        for k, spec in self.DESTINATION_PARAMS_SPEC.items():
            value = params.get(k, spec.get("default"))
            if spec.get('required') and not value:
                check_required.append(k)
            mapper = spec.get("map")
            parsed_params[k] = mapper(value)
        if check_required:
            raise AWSBatchRunnerException("AWSBatchJobRunner requires the following params to be provided: %s."
                                          % (', '.join(check_required)))

        # parse Platform
        platform = 'EC2'
        auto_platform = parsed_params.get('auto_platform')
        fargate_version = parsed_params.get('fargate_version')
        vcpu = parsed_params.get('vcpu')
        memory = parsed_params.get('memory')
        gpu = parsed_params.get('gpu')

        if auto_platform and not fargate_version:
            raise AWSBatchRunnerException("AWSBatchJobRunner needs 'farget_version' to be set to enable auto platform!")

        if gpu and (fargate_version or auto_platform):
            raise AWSBatchRunnerException("GPU mode is not allowed when 'fargate_version' and/or 'auto_platform' are set!")

        if fargate_version and not auto_platform:
            platform = 'FARGATE'
        if auto_platform:
            max_vcpu = self.FARGATE_VCPUS[-1]
            max_memory = self.FARGATE_RESOURCES[max_vcpu][-1]
            if vcpu <= max_vcpu and memory <= max_memory:
                new_vcpu, new_memory = None, None
                for c in self.FARGATE_VCPUS:
                    if c < vcpu:
                        continue
                    for m in self.FARGATE_RESOURCES[c]:
                        if m >= memory:     #Found the best match
                            new_vcpu = c
                            new_memory = m
                            break
                    if new_memory:
                        platform = 'FARGATE'
                        parsed_params['vcpu'] = new_vcpu
                        parsed_params['memory'] = new_memory
                        break
            # parse JOB QUEUE
            job_queues = parsed_params.get('job_queue').split(',')
            if len(job_queues) < 2:
                raise AWSBatchRunnerException(
                    "AWSBatchJobRunner needs TWO job queues ('Farget Queue, EC2 Qeueue')"
                    " when 'auto_platform' is enabled!"
                )
            parsed_params['job_queue'] = job_queues[platform == 'EC2'].strip()

        parsed_params['platform'] = platform
        return parsed_params

    def write_command(self, job_wrapper):
        # Create command script instead passing it in the container
        # preventing wrong characters parsing.
        if not os.path.exists(job_wrapper.working_directory):
            LOGGER.error("No working directory found")

        path = f"{job_wrapper.working_directory}/galaxy_{job_wrapper.get_id_tag()}.sh"
        mode = 0o755

        runner_command_line = job_wrapper.runner_command_line.replace(
            '> ../outputs/tool_stdout 2> ../outputs/tool_stderr', '')
        with open(path, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            f.write(runner_command_line)
        os.chmod(path, mode)
        return path

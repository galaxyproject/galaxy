""" Galaxy job runners to use Amazon AWS native compute resources, such as AWS Batch.
"""

import bisect
import hashlib
import json
import logging
import os
import re
import time
from queue import Empty
from typing import (
    Set,
    TYPE_CHECKING,
)

from galaxy import model
from galaxy.job_execution.output_collect import default_exit_code_file
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
    JobState,
)
from galaxy.util import (
    smart_str,
    unicodify,
)

if TYPE_CHECKING:
    from galaxy.jobs import MinimalJobWrapper

BOTO3_IMPORT_MSG = (
    "The Python 'boto3' package is required to use "
    "this feature, please install it or correct the "
    "following error:\nImportError {msg!s}"
)

try:
    import boto3
except ImportError as e:
    boto3 = None  # type: ignore[assignment]
    BOTO3_IMPORT_MSG.format(msg=unicodify(e))


__all__ = ("AWSBatchJobRunner",)
log = logging.getLogger(__name__)

STOP_SIGNAL = object()


class AWSBatchRunnerException(Exception):
    pass


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
        {"name": "GALAXY_MEMORY_MB", "value": str(memory)},
    ]


def _add_resource_requirements(destination_params):
    rval = [
        {"type": "VCPU", "value": str(destination_params.get("vcpu"))},
        {"type": "MEMORY", "value": str(destination_params.get("memory"))},
    ]
    if n_gpu := destination_params.get("gpu"):
        rval.append({"type": "GPU", "value": str(n_gpu)})
    return rval


class AWSBatchJobRunner(AsynchronousJobRunner):
    """
    This runner uses container only. It requires that an AWS EFS is mounted as a local drive
    and all Galaxy job-related paths, such as objects, job_directory, tool_directory and so
    on, are placed in the EFS drive. Via this runner, Galaxy jobs are dispatched to AWS Batch
    for compute using the docker image specified by a Galaxy tool. As AWS EFS is designed to
    be able to mount at multiple places with read and write capabilities, Galaxy and Batch
    containers share the same EFS drive as a local device. Sample configurations can be found
    in `config/job_conf.sample.yml`.
    """

    runner_name = "AWSBatchRunner"
    RUNNER_PARAM_SPEC_KEY = "runner_param_specs"
    JOB_NAME_PREFIX = "galaxy-"
    # AWS Batch queries up to 100 jobs at once.
    MAX_JOBS_PER_QUERY = 100
    # Higher minimum interval as jobs are queried in batches.
    MIN_QUERY_INTERVAL = 10

    # fmt: off
    RUNNER_PARAM_SPEC = {
        "aws_access_key_id": {
            "map": str,
        },
        "aws_secret_access_key": {
            "map": str,
        },
        "region": {
            "map": str,
        },
    }

    # fmt: off
    DESTINATION_PARAMS_SPEC = {
        "vcpu": {
            "default": 1.0,
            "map": (lambda x: int(float(x)) if int(float(x)) == float(x) else float(x)),
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
            "default": "",
            "map": str,
            "required": True,
        },
        "job_role_arn": {
            "default": "",
            "map": str,
            "required": True,
        },
        "efs_filesystem_id": {
            "default": "",
            "map": str,
            "required": True,
        },
        "efs_mount_point": {
            "default": "",
            "map": str,
            "required": True,
        },
        "execute_role_arn": {
            "default": "",
            "map": str,
        },
        "fargate_version": {
            "default": "",
            "map": str,
        },
        "auto_platform": {
            "default": False,
            "map": lambda x: str(x).lower() == "true",
        },
        "ec2_host_volumes": {
            "default": "",
            "map": str,
        },
        "privileged": {
            "default": False,
            "map": lambda x: str(x).lower() == "true",
        },
        "retry_attempts": {
            "default": 1,
            "map": int,
        },
        "retry_on_exit_statusReason": {
            "default": "",
            "map": str,
        },
        "retry_on_exit_reason": {
            "default": "",
            "map": str,
        },
        "retry_on_exit_exitCode": {
            "default": "",
            "map": str,
        },
        "retry_on_exit_action": {
            "default": "RETRY",
            "map": str,
        },
    }

    # fmt: off
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
            aws_access_key_id=self.runner_params.get("aws_access_key_id") or None,
            aws_secret_access_key=self.runner_params.get("aws_secret_access_key") or None,
            region_name=self.runner_params.get("region") or None,
        )
        self._batch_client = session.client("batch")

    def queue_job(self, job_wrapper):
        log.debug(f"Starting queue_job for job {job_wrapper.get_id_tag()}")
        if not self.prepare_job(job_wrapper, include_metadata=False, modify_command_for_container=False):
            log.debug(f"Not ready {job_wrapper.get_id_tag()}")
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
        container_image = self._find_container(job_wrapper).container_id
        h = hashlib.new("sha256")
        h.update(smart_str(container_image))
        s = json.dumps(destination_params, sort_keys=True)
        h.update(smart_str(s))
        queue_name = destination_params.get("job_queue").rsplit("/", 1)[-1]

        jd_name = f"galaxy_tool__{tool_id}__{h.hexdigest()}__{queue_name}"
        jd_name = re.sub(r'[^-_A-Za-z0-9]', '-', jd_name)[:128]
        res = self._batch_client.describe_job_definitions(jobDefinitionName=jd_name, status="ACTIVE")
        if not res["jobDefinitions"]:
            jd_arn = self._register_job_definition(jd_name, container_image, destination_params)
        else:
            jd_arn = res["jobDefinitions"][0]["jobDefinitionArn"]
            log.debug(f"Found existing job definition: {jd_name}.")

        return jd_arn

    def _get_mount_volumes(self, destination_params):
        volumes, mount_points = [], []
        volumes.append(
            {
                "name": "efs_whole",
                "efsVolumeConfiguration": {
                    "fileSystemId": destination_params.get("efs_filesystem_id"),
                    "rootDirectory": "/",
                    "transitEncryption": "ENABLED",
                    "authorizationConfig": {"iam": "ENABLED"},
                },
            },
        )
        mount_points.append(
            {
                "containerPath": destination_params.get("efs_mount_point"),
                "readOnly": False,
                "sourceVolume": "efs_whole",
            },
        )
        if destination_params.get("platform") == 'Fargate':   # Fargate doesn't support host volumes
            return volumes, mount_points

        if (ec2_host_volumes := destination_params.get("ec2_host_volumes")):
            for ix, vol in enumerate(ec2_host_volumes.split(",")):
                vol = vol.strip()
                vol_name = "host_vol_" + str(ix)
                volumes.append(
                    {
                        "name": vol_name,
                        "host": {"sourcePath": vol},
                    },
                )
                mount_points.append(
                    {
                        "containerPath": vol,
                        "readOnly": False,
                        "sourceVolume": vol_name,
                    },
                )
        return volumes, mount_points

    def _get_retry_strategy(self, destination_params):
        """ Make a simple one-condition retry strategy
        """
        # TODO make multi-condition retry strategies
        attemps = destination_params.get("retry_attempts")
        status_reason = destination_params.get("retry_on_exit_statusReason")
        reason = destination_params.get("retry_on_exit_reason")
        exit_code = destination_params.get("retry_on_exit_exitCode")
        action = destination_params.get("retry_on_exit_action")

        if attemps <= 1:
            return

        strategy = {
            "attempts": attemps,
            "evaluateOnExit": [{"action": action}],
        }
        if status_reason:
            strategy["evaluateOnExit"][0]["onStatusReason"] = status_reason
        if reason:
            strategy["evaluateOnExit"][0]["onReason"] = reason
        if exit_code:
            strategy["evaluateOnExit"][0]["onExitCode"] = exit_code
        return strategy

    def _register_job_definition(self, jd_name, container_image, destination_params):
        log.debug(f"Registering a new job definition: {jd_name}.")
        platform = destination_params.get("platform")
        volumes, mount_points = self._get_mount_volumes(destination_params)

        # TODO: support multi-node
        containerProperties = {
            "image": container_image,
            "command": [
                "/bin/sh",
            ],
            "jobRoleArn": destination_params.get("job_role_arn"),
            "executionRoleArn": destination_params.get("execute_role_arn") or destination_params.get("job_role_arn"),
            "volumes": volumes,
            "mountPoints": mount_points,
            "resourceRequirements": _add_resource_requirements(destination_params),
            "environment": _add_galaxy_environment_variables(
                destination_params.get("vcpu"), destination_params.get("memory"),
            ),
            "user": "%d:%d" % (os.getuid(), os.getgid()),
            "privileged": destination_params.get("privileged"),
            "logConfiguration": {"logDriver": "awslogs"},
        }
        if platform == "FARGATE":
            containerProperties.update(
                {
                    "networkConfiguration": {"assignPublicIp": "ENABLED"},
                    "fargatePlatformConfiguration": {"platformVersion": destination_params.get("fargate_version")},
                    "logConfiguration": {"logDriver": "awslogs"},
                }
            )
        other_kwargs = {}
        if (retry_strategy := self._get_retry_strategy(destination_params)):
            other_kwargs["retryStrategy"] = retry_strategy

        res = self._batch_client.register_job_definition(
            jobDefinitionName=jd_name,
            type="container",
            platformCapabilities=[platform],
            containerProperties=containerProperties,
            **other_kwargs,
        )

        assert res["ResponseMetadata"]["HTTPStatusCode"] == 200
        return res["jobDefinitionArn"]

    def _submit_job(self, job_def, job_wrapper, destination_params):
        job_name = self.JOB_NAME_PREFIX + job_wrapper.get_id_tag()
        command_script_path = self.write_command(job_wrapper)

        log.info(f"Submitting job {job_name} to AWS Batch.")
        res = self._batch_client.submit_job(
            jobName=job_name,
            jobQueue=destination_params.get("job_queue"),
            jobDefinition=job_def,
            containerOverrides={
                "command": [
                    "/bin/bash",
                    f"{command_script_path}",
                ]
            },
        )

        assert res["ResponseMetadata"]["HTTPStatusCode"] == 200
        return job_name, res["jobId"]

    def stop_job(self, job_wrapper):
        job = job_wrapper.get_job()
        external_id = job.get_job_runner_external_id()
        job_name = self.JOB_NAME_PREFIX + job_wrapper.get_id_tag()

        self._batch_client.terminate_job(jobId=external_id, reason="Terminated by Galaxy!")
        msg = "Job {name!r} is terminated"
        log.debug(msg.format(name=job_name))

    def recover(self, job, job_wrapper):
        msg = "(name!r/runner!r) is still in {state!s} state, adding to the runner monitor queue"
        job_id = job.get_job_runner_external_id()
        job_name = self.JOB_NAME_PREFIX + job_wrapper.get_id_tag()
        ajs = AsynchronousJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper,
            job_id=str(job_id),
            job_name=job_name,
            job_destination=job_wrapper.job_destination,
        )
        if job.state in (model.Job.states.RUNNING, model.Job.states.STOPPED):
            log.debug(msg.format(name=job.id, runner=job.job_runner_name, state=job.state))
            ajs.old_state = model.Job.states.RUNNING
            ajs.running = True
            self.monitor_queue.put(ajs)
        elif job.state == model.Job.states.QUEUED:
            log.debug(msg.format(name=job.id, runner=job.job_runner_name, state="queued"))
            ajs.old_state = model.Job.states.QUEUED
            ajs.running = False
            self.monitor_queue.put(ajs)

    def fail_job(self, job_state: JobState, exception=False, message="Job failed", full_status=None):
        job = job_state.job_wrapper.get_job()
        if getattr(job_state, "stop_job", True) and job.state != model.Job.states.NEW:
            self.stop_job(job_state.job_wrapper)
        job_state.job_wrapper.reclaim_ownership()
        self._handle_runner_state("failure", job_state)
        if not job_state.runner_state_handled:
            full_status = full_status or {}
            tool_stdout = full_status.get("stdout")
            tool_stderr = full_status.get("stderr")
            fail_message = getattr(job_state, "fail_message", message)
            job_state.job_wrapper.fail(
                fail_message, tool_stdout=tool_stdout, tool_stderr=tool_stderr, exception=exception
            )
            self._finish_or_resubmit_job(job_state, "", fail_message)
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
                log.exception("Unhandled exception checking active jobs")
            # Sleep a bit before the next state check
            time.sleep(max(self.app.config.job_runner_monitor_sleep, self.MIN_QUERY_INTERVAL))

    def check_watched_items(self):
        done: Set[str] = set()
        self.check_watched_items_by_batch(0, len(self.watched), done)
        self.watched = [x for x in self.watched if x[0] not in done]

    def check_watched_items_by_batch(self, start: int, end: int, done: Set[str]):
        jobs = self.watched[start : start + self.MAX_JOBS_PER_QUERY]
        if not jobs:
            return

        jobs_dict = dict(jobs)
        resp = self._batch_client.describe_jobs(jobs=list(jobs_dict.keys()))

        gotten = set()
        for job in resp["jobs"]:
            status = job["status"]
            job_id = job["jobId"]
            gotten.add(job_id)
            job_state = jobs_dict[job_id]

            if status == "SUCCEEDED":
                self._mark_as_successful(job_state)
                done.add(job_id)
            elif status == "FAILED":
                reason = job["statusReason"]
                self._mark_as_failed(job_state, reason)
                done.add(job_id)
            elif status in ("STARTING", "RUNNING"):
                self._mark_as_active(job_state)
            # remain queued for "SUBMITTED", "PENDING" and "RUNNABLE"
            # TODO else?

        for job_id in jobs_dict:
            if job_id in gotten:
                continue
            job_state = jobs_dict[job_id]
            reason = f"The track of Job {job_state} was lost for unknown reason!"
            self._mark_as_failed(job_state, reason)
            done.add(job_id)

        self.check_watched_items_by_batch(start + self.MAX_JOBS_PER_QUERY, end, done)

    def _mark_as_successful(self, job_state):
        _write_logfile(job_state.output_file, "")
        _write_logfile(job_state.error_file, "")
        job_state.running = False
        self.mark_as_finished(job_state)

    def _mark_as_active(self, job_state):
        job_state.running = True
        job_state.job_wrapper.change_state(model.Job.states.RUNNING)

    def _mark_as_failed(self, job_state, reason):
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
            if spec.get("required") and not value:
                check_required.append(k)
            mapper = spec.get("map")
            parsed_params[k] = mapper(value)  # type: ignore[operator]
        if check_required:
            raise AWSBatchRunnerException(
                "AWSBatchJobRunner requires the following params to be provided: {}.".format(", ".join(check_required))
            )

        # parse Platform
        platform = "EC2"
        auto_platform = parsed_params.get("auto_platform")
        fargate_version = parsed_params.get("fargate_version")
        vcpu = parsed_params.get("vcpu")
        memory = parsed_params.get("memory")
        gpu = parsed_params.get("gpu")

        if auto_platform and not fargate_version:
            raise AWSBatchRunnerException("AWSBatchJobRunner needs 'farget_version' to be set to enable auto platform!")

        if gpu and (fargate_version or auto_platform):
            raise AWSBatchRunnerException(
                "GPU mode is not allowed when 'fargate_version' and/or 'auto_platform' are set!"
            )

        if fargate_version and not auto_platform:
            platform = "FARGATE"
        if auto_platform:
            fargate_vcpus = list(self.FARGATE_RESOURCES.keys())
            max_vcpu = fargate_vcpus[-1]
            max_memory = self.FARGATE_RESOURCES[max_vcpu][-1]
            if vcpu <= max_vcpu and memory <= max_memory:  # type: ignore[operator]
                c_ix = bisect.bisect_left(fargate_vcpus, vcpu)  # type: ignore[type-var]
                length = len(fargate_vcpus)
                while c_ix < length:
                    c = fargate_vcpus[c_ix]
                    m_ix = bisect.bisect_left(self.FARGATE_RESOURCES[c], memory)  # type: ignore[type-var]
                    if m_ix < len(self.FARGATE_RESOURCES[c]):
                        platform = "FARGATE"
                        parsed_params["vcpu"] = c
                        parsed_params["memory"] = self.FARGATE_RESOURCES[c][m_ix]
                        break
                    c_ix += 1
            # parse JOB QUEUE
            job_queues = parsed_params.get("job_queue").split(",")  # type: ignore[union-attr]
            if len(job_queues) < 2:
                raise AWSBatchRunnerException(
                    "AWSBatchJobRunner needs to set TWO job queues ('Farget Queue, EC2 Qeueue')"
                    " when 'auto_platform' is enabled!"
                )
            parsed_params["job_queue"] = job_queues[platform == "EC2"].strip()

        if platform == "Fargate" and parsed_params.get("ec2_host_volumes") and not auto_platform:
            raise AWSBatchRunnerException(
                "AWSBatchJobRunner: param 'ec2_host_volumes' only works for EC2 platform"
                " unless 'auto_platform' is enabled!"
            )

        parsed_params["platform"] = platform
        return parsed_params

    def write_command(self, job_wrapper: "MinimalJobWrapper") -> str:
        # Create command script instead passing it in the container
        # preventing wrong characters parsing.
        command_line = job_wrapper.runner_command_line
        job_id = job_wrapper.get_id_tag()
        job_file = JobState.default_job_file(job_wrapper.working_directory, job_id)
        exit_code_path = default_exit_code_file(job_wrapper.working_directory, job_id)
        job_script_props = {
            "command": command_line,
            "exit_code_path": exit_code_path,
            "working_directory": job_wrapper.working_directory,
            "shell": job_wrapper.shell,
            "galaxy_virtual_env": None,
        }
        job_file_contents = self.get_job_file(job_wrapper, **job_script_props)
        self.write_executable_script(job_file, job_file_contents, job_io=job_wrapper.job_io)
        return job_file

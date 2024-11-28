"""Job runner used to execute Galaxy jobs through Pulsar.

More information on Pulsar can be found at https://pulsar.readthedocs.io/ .
"""

import copy
import errno
import logging
import os
import re
import subprocess
from time import sleep
from typing import (
    Any,
    Dict,
    Optional,
)

import pulsar.core
import yaml
from packaging.version import Version
from pulsar.client import (
    build_client_manager,
    CLIENT_INPUT_PATH_TYPES,
    ClientInput,
    ClientInputs,
    ClientJobDescription,
    ClientOutputs,
    EXTENDED_METADATA_DYNAMIC_COLLECTION_PATTERN,
    finish_job as pulsar_finish_job,
    PathMapper,
    PulsarClientTransportError,
    PulsarOutputs,
    submit_job as pulsar_submit_job,
    url_to_destination_params,
)

# TODO: Perform pulsar release with this included in the client package
from pulsar.client.staging import DEFAULT_DYNAMIC_COLLECTION_PATTERN
from sqlalchemy import select

from galaxy import model
from galaxy.job_execution.compute_environment import (
    ComputeEnvironment,
    dataset_path_to_extra_path,
)
from galaxy.jobs import JobDestination
from galaxy.jobs.command_factory import build_command
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
    JobState,
)
from galaxy.model.base import check_database_connection
from galaxy.tool_util.deps import dependencies
from galaxy.util import (
    galaxy_directory,
    specs,
    string_as_bool_or_none,
    unicodify,
)

log = logging.getLogger(__name__)

__all__ = (
    "PulsarLegacyJobRunner",
    "PulsarRESTJobRunner",
    "PulsarMQJobRunner",
    "PulsarEmbeddedJobRunner",
    "PulsarEmbeddedMQJobRunner",
)

MINIMUM_PULSAR_VERSIONS = {
    "_default_": Version("0.7.0.dev3"),
    "remote_metadata": Version("0.8.0"),
    "remote_container_handling": Version("0.9.1.dev0"),  # probably 0.10 ultimately?
}

NO_REMOTE_GALAXY_FOR_METADATA_MESSAGE = "Pulsar misconfiguration - Pulsar client configured to set metadata remotely, but remote Pulsar isn't properly configured with a galaxy_home directory."
NO_REMOTE_DATATYPES_CONFIG = "Pulsar client is configured to use remote datatypes configuration when setting metadata externally, but Pulsar is not configured with this information. Defaulting to datatypes_conf.xml."
GENERIC_REMOTE_ERROR = "Failed to communicate with remote job server."
FAILED_REMOTE_ERROR = "Remote job server indicated a problem running or monitoring this job."
LOST_REMOTE_ERROR = "Remote job server could not determine this job's state."

UPGRADE_PULSAR_ERROR = "Galaxy is misconfigured, please contact administrator. The target Pulsar server is unsupported, this version of Galaxy requires Pulsar version %s or newer."

# Is there a good way to infer some default for this? Can only use
# url_for from web threads. https://gist.github.com/jmchilton/9098762
DEFAULT_GALAXY_URL = "http://localhost:8080"

PULSAR_PARAM_SPECS = dict(
    transport=dict(map=specs.to_str_or_none, valid=specs.is_in("urllib", "curl", None), default=None),
    transport_timeout=dict(
        map=lambda val: None if val == "None" else int(val),
        default=None,
    ),
    cache=dict(
        map=specs.to_bool_or_none,
        default=None,
    ),
    remote_container_handling=dict(
        map=specs.to_bool,
        default=False,
    ),
    amqp_url=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    amqp_key_prefix=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    galaxy_url=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    secret=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    pulsar_config=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    pulsar_app_config=dict(
        default=None,
    ),
    manager=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    persistence_directory=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    amqp_acknowledge=dict(map=specs.to_bool_or_none, default=None),
    amqp_ack_republish_time=dict(
        map=lambda val: None if val == "None" else int(val),
        default=None,
    ),
    amqp_consumer_timeout=dict(
        map=lambda val: None if val == "None" else float(val),
        default=None,
    ),
    amqp_connect_ssl_ca_certs=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    amqp_connect_ssl_keyfile=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    amqp_connect_ssl_certfile=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    amqp_connect_ssl_cert_reqs=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    # https://kombu.readthedocs.io/en/latest/reference/kombu.html#kombu.Producer.publish
    amqp_publish_retry=dict(
        map=specs.to_bool,
        default=False,
    ),
    amqp_publish_priority=dict(
        map=int,
        valid=lambda x: 0 <= x and x <= 9,
        default=0,
    ),
    # https://kombu.readthedocs.io/en/latest/reference/kombu.html#kombu.Exchange.delivery_mode
    amqp_publish_delivery_mode=dict(
        map=str,
        valid=specs.is_in("transient", "persistent"),
        default="persistent",
    ),
    amqp_publish_retry_max_retries=dict(
        map=int,
        default=None,
    ),
    amqp_publish_retry_interval_start=dict(
        map=int,
        default=None,
    ),
    amqp_publish_retry_interval_step=dict(
        map=int,
        default=None,
    ),
    amqp_publish_retry_interval_max=dict(
        map=int,
        default=None,
    ),
)


PARAMETER_SPECIFICATION_REQUIRED = object()
PARAMETER_SPECIFICATION_IGNORED = object()


class PulsarJobRunner(AsynchronousJobRunner):
    """Base class for pulsar job runners."""

    start_methods = ["_init_worker_threads", "_init_client_manager", "_monitor"]
    runner_name = "PulsarJobRunner"
    default_build_pulsar_app = False
    use_mq = False
    poll = True

    def __init__(self, app, nworkers, **kwds):
        """Start the job runner."""
        super().__init__(app, nworkers, runner_param_specs=PULSAR_PARAM_SPECS, **kwds)
        galaxy_url = self.runner_params.galaxy_url
        if not galaxy_url:
            galaxy_url = app.config.galaxy_infrastructure_url
        if galaxy_url:
            galaxy_url = galaxy_url.rstrip("/")
        self.galaxy_url = galaxy_url

    def _monitor(self):
        if self.use_mq:
            # This is a message queue driven runner, don't monitor
            # just setup required callback.
            self.client_manager.ensure_has_status_update_callback(self.__async_update)
            self.client_manager.ensure_has_ack_consumers()

        if self.poll:
            self._init_monitor_thread()
        else:
            self._init_noop_monitor()

    def _init_client_manager(self):
        pulsar_conf = self.runner_params.get("pulsar_app_config", None)
        pulsar_conf_file = None
        if pulsar_conf is None:
            pulsar_conf_file = self.runner_params.get("pulsar_config", None)
        self.__init_pulsar_app(pulsar_conf, pulsar_conf_file)

        client_manager_kwargs = {}
        for kwd in "manager", "cache", "transport", "persistence_directory":
            client_manager_kwargs[kwd] = self.runner_params[kwd]
        if self.pulsar_app is not None:
            client_manager_kwargs["pulsar_app"] = self.pulsar_app
            # TODO: Hack remove this following line pulsar lib update
            # that includes https://github.com/galaxyproject/pulsar/commit/ce0636a5b64fae52d165bcad77b2caa3f0e9c232
            client_manager_kwargs["file_cache"] = None

        for kwd in self.runner_params.keys():
            if kwd.startswith("amqp_") or kwd.startswith("transport_"):
                client_manager_kwargs[kwd] = self.runner_params[kwd]
        self.client_manager = build_client_manager(**client_manager_kwargs)

    def __init_pulsar_app(self, conf, pulsar_conf_path):
        if conf is None and pulsar_conf_path is None and not self.default_build_pulsar_app:
            self.pulsar_app = None
            return
        if conf is None:
            conf = {}
            if pulsar_conf_path is None:
                log.info("Creating a Pulsar app with default configuration (no pulsar_conf specified).")
            else:
                log.info(f"Loading Pulsar app configuration from {pulsar_conf_path}")
                with open(pulsar_conf_path) as f:
                    conf.update(yaml.safe_load(f) or {})
        if "job_metrics_config_file" not in conf:
            conf["job_metrics"] = self.app.job_metrics
        if "staging_directory" not in conf:
            conf["staging_directory"] = os.path.join(self.app.config.data_dir, "pulsar_staging")
        if "persistence_directory" not in conf:
            conf["persistence_directory"] = os.path.join(self.app.config.data_dir, "pulsar_persisted_data")
        if "galaxy_home" not in conf:
            conf["galaxy_home"] = galaxy_directory()
        self.pulsar_app = pulsar.core.PulsarApp(**conf)

    def url_to_destination(self, url):
        """Convert a legacy URL to a job destination."""
        return JobDestination(runner="pulsar", params=url_to_destination_params(url))

    def check_watched_item(self, job_state):
        if self.use_mq:
            # Might still need to check pod IPs.
            job_wrapper = job_state.job_wrapper
            guest_ports = job_wrapper.guest_ports
            if len(guest_ports) > 0:
                persisted_state = job_wrapper.get_state()
                if persisted_state in model.Job.terminal_states + [model.Job.states.DELETING]:
                    log.debug(
                        "(%s) Watched job in terminal state, will stop monitoring: %s",
                        job_state.job_id,
                        persisted_state,
                    )
                    job_state = None
                elif persisted_state == model.Job.states.RUNNING:
                    client = self.get_client_from_state(job_state)
                    job_ip = client.job_ip()
                    if job_ip:
                        ports_dict = {}
                        for guest_port in guest_ports:
                            ports_dict[str(guest_port)] = dict(host=job_ip, port=guest_port, protocol="http")
                        self.app.interactivetool_manager.configure_entry_points(job_wrapper.get_job(), ports_dict)
                        log.debug("(%s) Got ports for entry point: %s", job_state.job_id, str(ports_dict))
                        job_state = None
            else:
                # No need to monitor MQ jobs that have no entry points
                job_state = None
            return job_state
        else:
            return self.check_watched_item_state(job_state)

    def check_watched_item_state(self, job_state):
        try:
            client = self.get_client_from_state(job_state)
            status = client.get_status()
        except PulsarClientTransportError as exc:
            log.error("Communication error with Pulsar server on state check, will retry: %s", exc)
            return job_state
        except Exception:
            # An orphaned job was put into the queue at app startup, so remote server went down
            # either way we are done I guess.
            self.mark_as_finished(job_state)
            return None
        job_state = self._update_job_state_for_status(job_state, status)
        return job_state

    def _update_job_state_for_status(self, job_state, pulsar_status, full_status=None):
        log.debug("(%s) Received status update: %s", job_state.job_id, pulsar_status)
        if pulsar_status in ["complete", "cancelled"]:
            self.mark_as_finished(job_state)
            return None
        if job_state.job_wrapper.get_state() == model.Job.states.STOPPED:
            client = self.get_client_from_state(job_state)
            client.kill()
            self.mark_as_finished(job_state)
            return None
        if pulsar_status in ["failed", "lost"]:
            if pulsar_status == "failed":
                message = FAILED_REMOTE_ERROR
            else:
                message = LOST_REMOTE_ERROR
            if not job_state.job_wrapper.get_job().finished:
                self.fail_job(job_state, message=message, full_status=full_status)
            return None
        if pulsar_status == "running" and not job_state.running:
            job_state.running = True
            job_state.job_wrapper.change_state(model.Job.states.RUNNING)
        return job_state

    def queue_job(self, job_wrapper):
        job_destination = job_wrapper.job_destination
        self._populate_parameter_defaults(job_destination)

        command_line, client, remote_job_config, compute_environment, remote_container = self.__prepare_job(
            job_wrapper, job_destination
        )

        if not command_line:
            return

        try:
            dependencies_description = PulsarJobRunner.__dependencies_description(client, job_wrapper)
            rewrite_paths = not PulsarJobRunner.__rewrite_parameters(client)
            path_rewrites_unstructured = {}
            output_names = []
            if compute_environment:
                path_rewrites_unstructured = compute_environment.path_rewrites_unstructured
                output_names = compute_environment.output_names()

                client_inputs_list = []
                for input_dataset_wrapper in job_wrapper.job_io.get_input_paths():
                    # str here to resolve false_path if set on a DatasetPath object.
                    path = str(input_dataset_wrapper)
                    object_store_ref = {
                        "dataset_id": input_dataset_wrapper.dataset_id,
                        "dataset_uuid": str(input_dataset_wrapper.dataset_uuid),
                        "object_store_id": input_dataset_wrapper.object_store_id,
                    }
                    client_inputs_list.append(
                        ClientInput(path, CLIENT_INPUT_PATH_TYPES.INPUT_PATH, object_store_ref=object_store_ref)
                    )

                for input_extra_path in compute_environment.path_rewrites_input_extra.keys():
                    # TODO: track dataset for object_Store_ref...
                    client_inputs_list.append(
                        ClientInput(input_extra_path, CLIENT_INPUT_PATH_TYPES.INPUT_EXTRA_FILES_PATH)
                    )

                for input_metadata_path in compute_environment.path_rewrites_input_metadata.keys():
                    # TODO: track dataset for object_Store_ref...
                    client_inputs_list.append(
                        ClientInput(input_metadata_path, CLIENT_INPUT_PATH_TYPES.INPUT_METADATA_PATH)
                    )

                input_files = None
                client_inputs = ClientInputs(client_inputs_list)
            else:
                input_files = self.get_input_files(job_wrapper)
                client_inputs = None

            if self.app.config.metadata_strategy == "legacy":
                # Drop this branch in 19.09.
                metadata_directory = job_wrapper.working_directory
            else:
                metadata_directory = os.path.join(job_wrapper.working_directory, "metadata")

            dest_params = job_destination.params
            remote_pulsar_app_config = dest_params.get("pulsar_app_config", {}).copy()
            if "pulsar_app_config_path" in dest_params:
                pulsar_app_config_path = dest_params["pulsar_app_config_path"]
                with open(pulsar_app_config_path) as fh:
                    remote_pulsar_app_config.update(yaml.safe_load(fh))
            job_directory_files = []
            config_files = job_wrapper.extra_filenames
            tool_script = os.path.join(job_wrapper.working_directory, "tool_script.sh")
            if os.path.exists(tool_script):
                log.debug(f"Registering tool_script for Pulsar transfer [{tool_script}]")
                job_directory_files.append(tool_script)
                config_files.append(tool_script)
            # Following is job destination environment variables
            env = client.env
            # extend it with tool defined environment variables
            tool_envs = job_wrapper.environment_variables
            env.extend(tool_envs)
            for tool_env in tool_envs:
                job_directory_path = tool_env.get("job_directory_path")
                if job_directory_path:
                    config_files.append(job_directory_path)
            tool_directory_required_files = job_wrapper.tool.required_files
            client_job_description = ClientJobDescription(
                command_line=command_line,
                input_files=input_files,
                client_inputs=client_inputs,  # Only one of these input defs should be non-None
                client_outputs=self.__client_outputs(client, job_wrapper),
                working_directory=job_wrapper.tool_working_directory,
                metadata_directory=metadata_directory,
                tool=job_wrapper.tool,
                config_files=config_files,
                dependencies_description=dependencies_description,
                env=env,
                rewrite_paths=rewrite_paths,
                arbitrary_files=path_rewrites_unstructured,
                touch_outputs=output_names,
                remote_pulsar_app_config=remote_pulsar_app_config,
                job_directory_files=job_directory_files,
                container=None if not remote_container else remote_container.container_id,
                guest_ports=job_wrapper.guest_ports,
                tool_directory_required_files=tool_directory_required_files,
            )
            external_job_id = pulsar_submit_job(client, client_job_description, remote_job_config)
            log.info(f"Pulsar job submitted with job_id {external_job_id}")
            job = job_wrapper.get_job()
            # Set the job destination here (unlike other runners) because there are likely additional job destination
            # params from the Pulsar client.
            # Flush with change_state.
            job_wrapper.set_job_destination(job_destination, external_id=external_job_id, flush=False, job=job)
            job_wrapper.change_state(model.Job.states.QUEUED, job=job)
        except Exception:
            job_wrapper.fail("failure running job", exception=True)
            log.exception("failure running job %d", job_wrapper.job_id)
            return

        pulsar_job_state = AsynchronousJobState(
            job_wrapper=job_wrapper, job_id=external_job_id, job_destination=job_destination
        )
        pulsar_job_state.old_state = True
        pulsar_job_state.running = False
        self.monitor_job(pulsar_job_state)

    def __needed_features(self, client):
        return {
            "remote_metadata": PulsarJobRunner.__remote_metadata(client),
            "remote_container_handling": PulsarJobRunner.__remote_container_handling(client),
        }

    def __prepare_job(self, job_wrapper, job_destination):
        """Build command-line and Pulsar client for this job."""
        command_line = None
        client = None
        remote_job_config = None
        compute_environment: Optional[PulsarComputeEnvironment] = None
        remote_container = None

        fail_or_resubmit = False
        try:
            client = self.get_client_from_wrapper(job_wrapper)
            tool = job_wrapper.tool
            remote_job_config = client.setup(tool.id, tool.version, tool.requires_galaxy_python_environment)
            remote_container_handling = PulsarJobRunner.__remote_container_handling(client)
            if remote_container_handling:
                # Handle this remotely and don't pass it to build_command
                remote_container = self._find_container(
                    job_wrapper,
                )

            needed_features = self.__needed_features(client)
            PulsarJobRunner.check_job_config(remote_job_config, check_features=needed_features)
            rewrite_parameters = PulsarJobRunner.__rewrite_parameters(client)
            prepare_kwds = {}
            if rewrite_parameters:
                compute_environment = PulsarComputeEnvironment(client, job_wrapper, remote_job_config)
                prepare_kwds["compute_environment"] = compute_environment
            job_wrapper.prepare(**prepare_kwds)
            self.__prepare_input_files_locally(job_wrapper)
            remote_metadata = PulsarJobRunner.__remote_metadata(client)
            dependency_resolution = PulsarJobRunner.__dependency_resolution(client)
            metadata_kwds = self.__build_metadata_configuration(
                client,
                job_wrapper,
                remote_metadata,
                remote_job_config,
                compute_environment=compute_environment,
            )
            remote_working_directory = remote_job_config["working_directory"]
            remote_job_directory = os.path.abspath(os.path.join(remote_working_directory, os.path.pardir))
            remote_tool_directory = os.path.abspath(os.path.join(remote_job_directory, "tool_files"))
            pulsar_version = PulsarJobRunner.pulsar_version(remote_job_config)
            remote_command_params = dict(
                working_directory=remote_job_config["metadata_directory"],
                script_directory=remote_job_directory,
                metadata_kwds=metadata_kwds,
                dependency_resolution=dependency_resolution,
                pulsar_version=pulsar_version,
            )
            rewrite_paths = not PulsarJobRunner.__rewrite_parameters(client)
            if pulsar_version < Version("0.14.999") and rewrite_paths:
                job_wrapper.disable_commands_in_new_shell()
            container = None
            if remote_container is None:
                container = self._find_container(
                    job_wrapper,
                    compute_working_directory=remote_working_directory,
                    compute_tool_directory=remote_tool_directory,
                    compute_job_directory=remote_job_directory,
                )

            # Pulsar handles ``create_tool_working_directory`` and
            # ``include_work_dir_outputs`` details.
            command_line = build_command(
                self,
                job_wrapper=job_wrapper,
                container=container,
                include_metadata=remote_metadata,
                create_tool_working_directory=False,
                include_work_dir_outputs=False,
                remote_command_params=remote_command_params,
                remote_job_directory=remote_job_directory,
            )
        except UnsupportedPulsarException:
            log.exception("failure running job %d, unsupported Pulsar target", job_wrapper.job_id)
            fail_or_resubmit = True
        except PulsarClientTransportError:
            log.exception("failure running job %d, Pulsar connection failed", job_wrapper.job_id)
            fail_or_resubmit = True
        except Exception:
            log.exception("failure running job %d", job_wrapper.job_id)
            fail_or_resubmit = True

        # If we were unable to get a command line, there was problem
        fail_or_resubmit = fail_or_resubmit or not command_line
        if fail_or_resubmit:
            job_state = self._job_state(job_wrapper.get_job(), job_wrapper)
            self.work_queue.put((self.fail_job, job_state))

        return command_line, client, remote_job_config, compute_environment, remote_container

    def __prepare_input_files_locally(self, job_wrapper):
        """Run task splitting commands locally."""
        prepare_input_files_cmds = getattr(job_wrapper, "prepare_input_files_cmds", None)
        if prepare_input_files_cmds is not None:
            for cmd in prepare_input_files_cmds:  # run the commands to stage the input files
                subprocess.check_call(cmd, shell=True)
            job_wrapper.prepare_input_files_cmds = None  # prevent them from being used in-line

    def _populate_parameter_defaults(self, job_destination):
        updated = False
        params = job_destination.params
        for key, value in self.destination_defaults.items():
            if key in params:
                if value is PARAMETER_SPECIFICATION_IGNORED:
                    log.warning(f"Pulsar runner in selected configuration ignores parameter {key}")
                continue
            # if self.runner_params.get( key, None ):
            #    # Let plugin define defaults for some parameters -
            #    # for instance that way jobs_directory can be
            #    # configured next to AMQP url (where it belongs).
            #    params[ key ] = self.runner_params[ key ]
            #    continue

            if not value:
                continue

            if value is PARAMETER_SPECIFICATION_REQUIRED:
                raise Exception(f"Pulsar destination does not define required parameter {key}")
            elif value is not PARAMETER_SPECIFICATION_IGNORED:
                params[key] = value
                updated = True
        return updated

    def get_output_files(self, job_wrapper):
        output_paths = job_wrapper.job_io.get_output_fnames()
        return [str(o) for o in output_paths]  # Force job_path from DatasetPath objects.

    def get_input_files(self, job_wrapper):
        input_paths = job_wrapper.job_io.get_input_paths()
        return [str(i) for i in input_paths]  # Force job_path from DatasetPath objects.

    def get_client_from_wrapper(self, job_wrapper):
        job_id = job_wrapper.job_id
        if hasattr(job_wrapper, "task_id"):
            job_id = f"{job_id}_{job_wrapper.task_id}"
        params = job_wrapper.job_destination.params.copy()
        if user := job_wrapper.get_job().user:
            for key, value in params.items():
                if value and isinstance(value, str):
                    params[key] = model.User.expand_user_properties(user, value)

        env = getattr(job_wrapper.job_destination, "env", [])
        return self.get_client(params, job_id, env)

    def get_client_from_state(self, job_state):
        job_destination_params = job_state.job_destination.params
        job_id = job_state.job_wrapper.job_id  # we want the Galaxy ID here, job_state.job_id is the external one.
        return self.get_client(job_destination_params, job_id)

    def get_client(self, job_destination_params, job_id, env=None):
        # Cannot use url_for outside of web thread.
        # files_endpoint = url_for( controller="job_files", job_id=encoded_job_id )
        if env is None:
            env = []
        encoded_job_id = self.app.security.encode_id(job_id)
        job_key = self.app.security.encode_id(job_id, kind="jobs_files")
        endpoint_base = "%s/api/jobs/%s/files?job_key=%s"
        if self.app.config.nginx_upload_job_files_path:
            endpoint_base = "%s" + self.app.config.nginx_upload_job_files_path + "?job_id=%s&job_key=%s"
        files_endpoint = endpoint_base % (self.galaxy_url, encoded_job_id, job_key)
        secret = job_destination_params.get("job_secret_base", "jobs_token")
        job_key = self.app.security.encode_id(job_id, kind=secret)
        token_endpoint = f"{self.galaxy_url}/api/jobs/{encoded_job_id}/oidc-tokens?job_key={job_key}"
        get_client_kwds = dict(
            job_id=str(job_id), files_endpoint=files_endpoint, token_endpoint=token_endpoint, env=env
        )
        # Turn MutableDict into standard dict for pulsar consumption
        job_destination_params = dict(job_destination_params.items())
        return self.client_manager.get_client(job_destination_params, **get_client_kwds)

    def finish_job(self, job_state: JobState):
        assert isinstance(
            job_state, AsynchronousJobState
        ), f"job_state type is '{type(job_state)}', expected AsynchronousJobState"
        job_wrapper = job_state.job_wrapper
        try:
            client = self.get_client_from_state(job_state)
            run_results = client.full_status()
            remote_metadata_directory = run_results.get("metadata_directory", None)
            tool_stdout = unicodify(run_results.get("stdout", ""), strip_null=True)
            tool_stderr = unicodify(run_results.get("stderr", ""), strip_null=True)
            for file in ("tool_stdout", "tool_stderr"):
                if tool_stdout and tool_stderr:
                    pass
                try:
                    file_path = os.path.join(job_wrapper.working_directory, "outputs", file)
                    file_content = open(file_path)
                    if tool_stdout is None and file == "tool_stdout":
                        tool_stdout = file_content.read()
                    elif tool_stderr is None and file == "tool_stderr":
                        tool_stderr = file_content.read()
                except Exception:
                    pass
            job_stdout = run_results.get("job_stdout")
            job_stderr = run_results.get("job_stderr")
            exit_code = run_results.get("returncode")
            pulsar_outputs = PulsarOutputs.from_status_response(run_results)
            state = job_wrapper.get_state()
            # Use Pulsar client code to transfer/copy files back
            # and cleanup job if needed.
            completed_normally = state not in [model.Job.states.ERROR, model.Job.states.DELETED]
            if completed_normally and state == model.Job.states.STOPPED:
                # Discard pulsar exit code (probably -9), we know the user stopped the job
                log.debug("Setting exit code for stopped job {job_wrapper.job_id} to 0 (was {exit_code})")
                exit_code = 0
            cleanup_job = job_wrapper.cleanup_job
            client_outputs = self.__client_outputs(client, job_wrapper)
            finish_args = dict(
                client=client,
                job_completed_normally=completed_normally,
                cleanup_job=cleanup_job,
                client_outputs=client_outputs,
                pulsar_outputs=pulsar_outputs,
            )
            failed = pulsar_finish_job(**finish_args)
            if failed:
                job_wrapper.fail(
                    "Failed to find or download one or more job outputs from remote server.", exception=True
                )
        except Exception:
            self.fail_job(job_state, message=GENERIC_REMOTE_ERROR, exception=True)
            log.exception("failure finishing job %d", job_wrapper.job_id)
            return
        if not PulsarJobRunner.__remote_metadata(client):
            # we need an actual exit code file in the job working directory to detect job errors in the metadata script
            with open(
                os.path.join(job_wrapper.working_directory, f"galaxy_{job_wrapper.job_id}.ec"), "w"
            ) as exit_code_file:
                exit_code_file.write(str(exit_code))
            self._handle_metadata_externally(job_wrapper, resolve_requirements=True)
        job_metrics_directory = os.path.join(job_wrapper.working_directory, "metadata")
        # Finish the job
        try:
            job_wrapper.finish(
                tool_stdout,
                tool_stderr,
                exit_code,
                job_stdout=job_stdout,
                job_stderr=job_stderr,
                remote_metadata_directory=remote_metadata_directory,
                job_metrics_directory=job_metrics_directory,
            )
        except Exception:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True, job_metrics_directory=job_metrics_directory)

    def check_pid(self, pid):
        try:
            os.kill(pid, 0)
            return True
        except OSError as e:
            if e.errno == errno.ESRCH:
                log.debug("check_pid(): PID %d is dead" % pid)
            else:
                log.warning(
                    "check_pid(): Got errno %s when attempting to check PID %d: %s"
                    % (errno.errorcode[e.errno], pid, e.strerror)
                )
            return False

    def stop_job(self, job_wrapper):
        job = job_wrapper.get_job()
        if not job.job_runner_external_id:
            return
        # if our local job has JobExternalOutputMetadata associated, then our primary job has to have already finished
        client = self.get_client(job.destination_params, job.job_runner_external_id)
        job_ext_output_metadata = job.get_external_output_metadata()
        if not PulsarJobRunner.__remote_metadata(client) and job_ext_output_metadata:
            pid = job_ext_output_metadata[
                0
            ].job_runner_external_pid  # every JobExternalOutputMetadata has a pid set, we just need to take from one of them
            if pid in [None, ""]:
                log.warning(f"stop_job(): {job.id}: no PID in database for job, unable to stop")
                return
            pid = int(pid)
            if not self.check_pid(pid):
                log.warning("stop_job(): %s: PID %d was already dead or can't be signaled" % (job.id, pid))
                return
            for sig in [15, 9]:
                try:
                    os.killpg(pid, sig)
                except OSError as e:
                    log.warning(
                        "stop_job(): %s: Got errno %s when attempting to signal %d to PID %d: %s"
                        % (job.id, errno.errorcode[e.errno], sig, pid, e.strerror)
                    )
                    return  # give up
                sleep(2)
                if not self.check_pid(pid):
                    log.debug("stop_job(): %s: PID %d successfully killed with signal %d" % (job.id, pid, sig))
                    return
                else:
                    log.warning("stop_job(): %s: PID %d refuses to die after signaling TERM/KILL" % (job.id, pid))
        else:
            # Remote kill
            pulsar_url = job.job_runner_name
            job_id = job.job_runner_external_id
            log.debug(f"Attempt remote Pulsar kill of job with url {pulsar_url} and id {job_id}")
            client = self.get_client(job.destination_params, job_id)
            client.kill()

    def recover(self, job, job_wrapper):
        """Recover jobs stuck in the queued/running state when Galaxy started."""
        job_state = self._job_state(job, job_wrapper)
        job_wrapper.command_line = job.get_command_line()
        state = job.get_state()
        if state in [model.Job.states.RUNNING, model.Job.states.QUEUED, model.Job.states.STOPPED]:
            log.debug(f"(Pulsar/{job.id}) is still in {state} state, adding to the Pulsar queue")
            job_state.old_state = True
            job_state.running = state == model.Job.states.RUNNING
            self.monitor_queue.put(job_state)

    def shutdown(self):
        super().shutdown()
        self.client_manager.shutdown()
        if self.pulsar_app:
            self.pulsar_app.shutdown()

    def _job_state(self, job, job_wrapper):
        raw_job_id = job.get_job_runner_external_id() or job_wrapper.job_id
        job_state = AsynchronousJobState(
            job_wrapper=job_wrapper, job_id=raw_job_id, job_destination=job_wrapper.job_destination
        )
        # TODO: Determine why this is set when using normal message queue updates
        # but not CLI submitted MQ updates...
        job_state.runner_url = job_wrapper.get_job_runner_url()
        return job_state

    def __client_outputs(self, client, job_wrapper):
        metadata_directory = os.path.join(job_wrapper.working_directory, "metadata")
        metadata_strategy = job_wrapper.get_destination_configuration("metadata_strategy", None)
        tool = job_wrapper.tool
        tool_provided_metadata_file_path = tool.provided_metadata_file
        tool_provided_metadata_style = tool.provided_metadata_style

        dynamic_outputs = None  # use default
        if metadata_strategy == "extended" and PulsarJobRunner.__remote_metadata(client):
            # if Pulsar is doing remote metadata and the remote metadata is extended,
            # we only need to recover the final model store.
            dynamic_outputs = EXTENDED_METADATA_DYNAMIC_COLLECTION_PATTERN
            output_files = []
            work_dir_outputs = []
        else:
            # otherwise collect everything we might need
            dynamic_outputs = DEFAULT_DYNAMIC_COLLECTION_PATTERN[:]
            # grab discovered outputs...
            dynamic_outputs.extend(job_wrapper.tool.output_discover_patterns)
            # grab tool provided metadata (galaxy.json) also...
            dynamic_outputs.append(re.escape(tool_provided_metadata_file_path))
            output_files = self.get_output_files(job_wrapper)
            work_dir_outputs = self.get_work_dir_outputs(job_wrapper)
        dynamic_file_sources = [
            {
                "path": tool_provided_metadata_file_path,
                "type": "galaxy" if tool_provided_metadata_style == "default" else "legacy_galaxy",
            }
        ]
        client_outputs = ClientOutputs(
            working_directory=job_wrapper.tool_working_directory,
            metadata_directory=metadata_directory,
            work_dir_outputs=work_dir_outputs,
            output_files=output_files,
            version_file=job_wrapper.get_version_string_path(),
            dynamic_outputs=dynamic_outputs,
            dynamic_file_sources=dynamic_file_sources,
        )
        return client_outputs

    @staticmethod
    def pulsar_version(remote_job_config):
        pulsar_version = Version(remote_job_config.get("pulsar_version", "0.6.0"))
        return pulsar_version

    @staticmethod
    def check_job_config(remote_job_config, check_features=None):
        check_features = check_features or {}
        # 0.6.0 was newest Pulsar version that did not report it's version.
        pulsar_version = PulsarJobRunner.pulsar_version(remote_job_config)
        needed_version = Version("0.0.0")
        log.info(f"pulsar_version is {pulsar_version}")
        for feature, needed in list(check_features.items()) + [("_default_", True)]:
            if not needed:
                continue
            if pulsar_version < MINIMUM_PULSAR_VERSIONS[feature]:
                needed_version = max(needed_version, MINIMUM_PULSAR_VERSIONS[feature])
        if pulsar_version < needed_version:
            raise UnsupportedPulsarException(needed_version)

    @staticmethod
    def __dependencies_description(pulsar_client, job_wrapper):
        dependency_resolution = PulsarJobRunner.__dependency_resolution(pulsar_client)
        remote_dependency_resolution = dependency_resolution == "remote"
        if not remote_dependency_resolution:
            return None
        requirements = job_wrapper.tool.requirements
        installed_tool_dependencies = job_wrapper.tool.installed_tool_dependencies
        return dependencies.DependenciesDescription(
            requirements=requirements,
            installed_tool_dependencies=installed_tool_dependencies,
        )

    @staticmethod
    def __dependency_resolution(pulsar_client):
        dependency_resolution = pulsar_client.destination_params.get("dependency_resolution", "remote")
        if dependency_resolution not in ["none", "local", "remote"]:
            raise Exception(f"Unknown dependency_resolution value encountered {dependency_resolution}")
        return dependency_resolution

    @staticmethod
    def __remote_metadata(pulsar_client):
        remote_metadata = string_as_bool_or_none(pulsar_client.destination_params.get("remote_metadata", False))
        return remote_metadata

    @staticmethod
    def __remote_container_handling(pulsar_client):
        remote_container_handling = string_as_bool_or_none(
            pulsar_client.destination_params.get("remote_container_handling", False)
        )
        return remote_container_handling

    @staticmethod
    def __use_remote_datatypes_conf(pulsar_client):
        """Use remote metadata datatypes instead of Galaxy's.

        When setting remote metadata, use integrated datatypes from this
        Galaxy instance or use the datatypes config configured via the remote
        Pulsar.

        Both options are broken in different ways for same reason - datatypes
        may not match. One can push the local datatypes config to the remote
        server - but there is no guarentee these datatypes will be defined
        there. Alternatively, one can use the remote datatype config - but
        there is no guarentee that it will contain all the datatypes available
        to this Galaxy.
        """
        use_remote_datatypes = string_as_bool_or_none(
            pulsar_client.destination_params.get("use_remote_datatypes", False)
        )
        return use_remote_datatypes

    @staticmethod
    def __rewrite_parameters(pulsar_client):
        return string_as_bool_or_none(pulsar_client.destination_params.get("rewrite_parameters", False)) or False

    def __build_metadata_configuration(
        self,
        client,
        job_wrapper,
        remote_metadata,
        remote_job_config,
        compute_environment: Optional["PulsarComputeEnvironment"] = None,
    ):
        metadata_kwds: Dict[str, Any] = {}
        if remote_metadata:
            working_directory = remote_job_config["working_directory"]
            metadata_directory = remote_job_config["metadata_directory"]
            # For metadata calculation, we need to build a list of of output
            # file objects with real path indicating location on Galaxy server
            # and false path indicating location on compute server. Since the
            # Pulsar disables from_work_dir copying as part of the job command
            # line we need to take the list of output locations on the Pulsar
            # server (produced by job_wrapper.job_io.get_output_fnames() and for
            # each work_dir output substitute the effective path on the Pulsar
            # server relative to the remote working directory as the
            # false_path to send the metadata command generation module.
            work_dir_outputs = self.get_work_dir_outputs(job_wrapper, tool_working_directory=working_directory)
            outputs = job_wrapper.job_io.get_output_fnames()
            # copy fixes 'test/integration/test_pulsar_embedded_remote_metadata.py::test_tools[job_properties]'
            real_path_to_output = {o.real_path: copy.copy(o) for o in outputs}
            rewritten_outputs = []
            for pulsar_workdir_path, real_path in work_dir_outputs:
                work_dir_output = real_path_to_output.pop(real_path, None)
                if work_dir_output:
                    work_dir_output.false_path = pulsar_workdir_path
                    rewritten_outputs.append(work_dir_output)

            for output in real_path_to_output.values():
                if compute_environment:
                    output.false_path = compute_environment.path_mapper.remote_output_path_rewrite(str(output))
                rewritten_outputs.append(output)

            metadata_kwds["output_fnames"] = rewritten_outputs
            remote_system_properties = remote_job_config.get("system_properties", {})
            remote_galaxy_home = remote_system_properties.get("galaxy_home")
            if not job_wrapper.use_metadata_binary:
                if not remote_galaxy_home:
                    raise Exception(NO_REMOTE_GALAXY_FOR_METADATA_MESSAGE)
                metadata_kwds["exec_dir"] = remote_galaxy_home
                metadata_kwds["compute_tmp_dir"] = metadata_directory
                metadata_kwds["config_root"] = remote_galaxy_home
                default_config_file = os.path.join(remote_galaxy_home, "config/galaxy.ini")
                metadata_kwds["config_file"] = remote_system_properties.get("galaxy_config_file", default_config_file)
                metadata_kwds["dataset_files_path"] = remote_system_properties.get("galaxy_dataset_files_path", None)
            if PulsarJobRunner.__use_remote_datatypes_conf(client):
                remote_datatypes_config = remote_system_properties.get("galaxy_datatypes_config_file")
                if not remote_datatypes_config:
                    log.warning(NO_REMOTE_DATATYPES_CONFIG)
                    if not remote_galaxy_home:
                        raise Exception(NO_REMOTE_GALAXY_FOR_METADATA_MESSAGE)
                    remote_datatypes_config = os.path.join(remote_galaxy_home, "datatypes_conf.xml")
                metadata_kwds["datatypes_config"] = remote_datatypes_config
            else:
                datatypes_config = os.path.join(job_wrapper.working_directory, "registry.xml")
                self.app.datatypes_registry.to_xml_file(path=datatypes_config)
                # Ensure this file gets pushed out to the remote config dir.
                job_wrapper.extra_filenames.append(datatypes_config)
                metadata_kwds["datatypes_config"] = datatypes_config
        return metadata_kwds

    def __async_update(self, full_status):
        galaxy_job_id = None
        remote_job_id = None
        try:
            check_database_connection(self.sa_session)
            remote_job_id = full_status["job_id"]
            if len(remote_job_id) == 32:
                # It is a UUID - assign_ids = uuid in destination params...
                stmt = select(model.Job.id).filter(model.Job.job_runner_external_id == remote_job_id)
                galaxy_job_id = self.app.model.session.execute(stmt).scalar_one()
            else:
                galaxy_job_id = remote_job_id
            job, job_wrapper = self.app.job_manager.job_handler.job_queue.job_pair_for_id(galaxy_job_id)
            job_state = self._job_state(job, job_wrapper)
            self._update_job_state_for_status(job_state, full_status["status"], full_status=full_status)
        except Exception:
            log.exception(f"Failed to update Pulsar job status for job_id ({galaxy_job_id}/{remote_job_id})")
            raise
            # Nothing else to do? - Attempt to fail the job?


class PulsarLegacyJobRunner(PulsarJobRunner):
    """Flavor of Pulsar job runner mimicking behavior of old LWR runner."""

    destination_defaults = dict(
        rewrite_parameters="false",
        dependency_resolution="local",
    )


class PulsarMQJobRunner(PulsarJobRunner):
    """Flavor of Pulsar job runner with sensible defaults for message queue communication."""

    use_mq = True
    poll = False

    destination_defaults = dict(
        default_file_action="remote_transfer",
        rewrite_parameters="true",
        dependency_resolution="remote",
        jobs_directory=PARAMETER_SPECIFICATION_REQUIRED,
        url=PARAMETER_SPECIFICATION_IGNORED,
        private_token=PARAMETER_SPECIFICATION_IGNORED,
    )


DEFAULT_PULSAR_CONTAINER = "galaxy/pulsar-pod-staging:0.15.0.2"
COEXECUTION_DESTINATION_DEFAULTS = {
    "default_file_action": "remote_transfer",
    "rewrite_parameters": "true",
    "jobs_directory": "/pulsar_staging",
    "pulsar_container_image": DEFAULT_PULSAR_CONTAINER,
    "remote_container_handling": True,
    "url": PARAMETER_SPECIFICATION_IGNORED,
    "private_token": PARAMETER_SPECIFICATION_IGNORED,
}


class PulsarCoexecutionJobRunner(PulsarMQJobRunner):
    destination_defaults = COEXECUTION_DESTINATION_DEFAULTS

    def _populate_parameter_defaults(self, job_destination):
        super()._populate_parameter_defaults(job_destination)
        params = job_destination.params
        # Set some sensible defaults for Pulsar application that runs in staging container.
        if "pulsar_app_config" not in params:
            params["pulsar_app_config"] = {}
        pulsar_app_config = params["pulsar_app_config"]
        if "staging_directory" not in pulsar_app_config:
            # coexecution always uses a fixed path for staging directory
            pulsar_app_config["staging_directory"] = params.get("jobs_directory")


KUBERNETES_DESTINATION_DEFAULTS: Dict[str, Any] = {"k8s_enabled": True, **COEXECUTION_DESTINATION_DEFAULTS}


class PulsarKubernetesJobRunner(PulsarCoexecutionJobRunner):
    destination_defaults = KUBERNETES_DESTINATION_DEFAULTS
    poll = True  # Poll so we can check API for pod IP for ITs.


TES_DESTINATION_DEFAULTS: Dict[str, Any] = {
    "tes_url": PARAMETER_SPECIFICATION_REQUIRED,
    **COEXECUTION_DESTINATION_DEFAULTS,
}


class PulsarTesJobRunner(PulsarCoexecutionJobRunner):
    destination_defaults = TES_DESTINATION_DEFAULTS


class PulsarRESTJobRunner(PulsarJobRunner):
    """Flavor of Pulsar job runner with sensible defaults for RESTful usage."""

    destination_defaults = dict(
        default_file_action="transfer",
        rewrite_parameters="true",
        dependency_resolution="remote",
        url=PARAMETER_SPECIFICATION_REQUIRED,
    )


class PulsarEmbeddedJobRunner(PulsarJobRunner):
    """Flavor of Puslar job runner that runs Pulsar's server code directly within Galaxy.

    This is an appropriate job runner for when the desire is to use Pulsar staging
    but their is not need to run a remote service.
    """

    destination_defaults = dict(
        default_file_action="copy",
        rewrite_parameters="true",
        dependency_resolution="remote",
    )
    default_build_pulsar_app = True


class PulsarEmbeddedMQJobRunner(PulsarMQJobRunner):
    default_build_pulsar_app = True


class PulsarComputeEnvironment(ComputeEnvironment):
    def __init__(self, pulsar_client, job_wrapper, remote_job_config):
        self.pulsar_client = pulsar_client
        self.job_wrapper = job_wrapper
        self.local_path_config = job_wrapper.default_compute_environment()

        self.path_rewrites_unstructured = {}
        self.path_rewrites_input_extra = {}
        self.path_rewrites_input_metadata = {}

        # job_wrapper.prepare is going to expunge the job backing the following
        # computations, so precalculate these paths.
        self.path_mapper = PathMapper(pulsar_client, remote_job_config, self.local_path_config.working_directory())
        self._config_directory = remote_job_config["configs_directory"]
        self._working_directory = remote_job_config["working_directory"]
        self._sep = remote_job_config["system_properties"]["separator"]
        self._tool_dir = remote_job_config["tools_directory"]
        self._tmp_dir = remote_job_config.get("tmp_dir")
        self._shared_home_dir = remote_job_config.get("shared_home_dir")
        version_path = self.local_path_config.version_path()
        new_version_path = self.path_mapper.remote_version_path_rewrite(version_path)
        if new_version_path:
            version_path = new_version_path
        self._version_path = version_path

    def output_names(self):
        # Maybe this should use the path mapper, but the path mapper just uses basenames
        return self.job_wrapper.job_io.get_output_basenames()

    def input_path_rewrite(self, dataset):
        local_input_path_rewrite = self.local_path_config.input_path_rewrite(dataset)
        if local_input_path_rewrite is not None:
            local_input_path = local_input_path_rewrite
        else:
            local_input_path = dataset.get_file_name()
        remote_path = self.path_mapper.remote_input_path_rewrite(local_input_path)
        return remote_path

    def output_path_rewrite(self, dataset):
        local_output_path_rewrite = self.local_path_config.output_path_rewrite(dataset)
        if local_output_path_rewrite is not None:
            local_output_path = local_output_path_rewrite
        else:
            local_output_path = dataset.get_file_name()
        remote_path = self.path_mapper.remote_output_path_rewrite(local_output_path)
        return remote_path

    def input_extra_files_rewrite(self, dataset):
        input_path_rewrite = self.input_path_rewrite(dataset)
        remote_extra_files_path_rewrite = dataset_path_to_extra_path(input_path_rewrite)
        self.path_rewrites_input_extra[dataset.extra_files_path] = remote_extra_files_path_rewrite
        return remote_extra_files_path_rewrite

    def output_extra_files_rewrite(self, dataset):
        output_path_rewrite = self.output_path_rewrite(dataset)
        remote_extra_files_path_rewrite = dataset_path_to_extra_path(output_path_rewrite)
        return remote_extra_files_path_rewrite

    def input_metadata_rewrite(self, dataset, metadata_val):
        # May technically be incorrect to not pass through local_path_config.input_metadata_rewrite
        # first but that adds untested logic that wouln't ever be used.
        remote_input_path = self.path_mapper.remote_input_path_rewrite(
            metadata_val, client_input_path_type=CLIENT_INPUT_PATH_TYPES.INPUT_METADATA_PATH
        )
        if remote_input_path:
            log.info(f"input_metadata_rewrite is {remote_input_path} from {metadata_val}")
            self.path_rewrites_input_metadata[metadata_val] = remote_input_path
            return remote_input_path

        # No rewrite...
        return None

    def unstructured_path_rewrite(self, parameter_value):
        path_rewrites_unstructured = self.path_rewrites_unstructured
        if parameter_value in path_rewrites_unstructured:
            # Path previously mapped, use previous mapping.
            return path_rewrites_unstructured[parameter_value]

        rewrite, new_unstructured_path_rewrites = self.path_mapper.check_for_arbitrary_rewrite(parameter_value)
        if rewrite:
            path_rewrites_unstructured.update(new_unstructured_path_rewrites)
            return rewrite
        else:
            # Did not need to rewrite, use original path or value.
            return None

    def working_directory(self):
        return self._working_directory

    def env_config_directory(self):
        return self.config_directory()

    def config_directory(self):
        return self._config_directory

    def new_file_path(self):
        return self.working_directory()  # Problems with doing this?

    def sep(self):
        return self._sep

    def version_path(self):
        return self._version_path

    def tool_directory(self):
        return self._tool_dir

    def home_directory(self):
        return self._target_to_directory(self.job_wrapper.home_target)

    def tmp_directory(self):
        return self._target_to_directory(self.job_wrapper.tmp_target)

    def _target_to_directory(self, target):
        tmp_dir = self._tmp_dir
        if target is None or (target == "job_tmp_if_explicit" and tmp_dir is None):
            return None
        elif target in ["job_tmp", "job_tmp_if_explicit"]:
            return "$_GALAXY_JOB_TMP_DIR"
        elif target == "shared_home":
            return self._shared_home_dir
        elif target == "job_home":
            return "$_GALAXY_JOB_HOME_DIR"
        elif target == "pwd":
            os.path.join(self.working_directory(), "working")
        else:
            raise Exception(f"Unknown target type [{target}]")

    def galaxy_url(self):
        return self.job_wrapper.get_destination_configuration("galaxy_infrastructure_url")

    def get_file_sources_dict(self):
        return self.job_wrapper.job_io.file_sources_dict


class UnsupportedPulsarException(Exception):
    def __init__(self, needed):
        super().__init__(UPGRADE_PULSAR_ERROR % needed)

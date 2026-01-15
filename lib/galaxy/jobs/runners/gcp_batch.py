"""
Google Cloud Batch Job Runner

This runner submits Galaxy jobs to Google Cloud Batch for execution.
"""

import json
import logging
import os
import re
import time
from typing import (
    Any,
    Dict,
)

from google.api_core import exceptions as gcp_exceptions
from google.auth import default
from google.cloud import batch_v1

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.jobs.runners.util.gcp_batch import (
    CONTAINER_SCRIPT_TEMPLATE,
    DEFAULT_CVMFS_DOCKER_VOLUME,
    DEFAULT_MEMORY_MIB,
    DEFAULT_NFS_MOUNT_PATH,
    DEFAULT_NFS_PATH,
    DIRECT_SCRIPT_TEMPLATE,
    convert_cpu_to_milli,
    convert_memory_to_mib,
    parse_docker_volumes_param,
    parse_volumes_param,
    sanitize_label_value,
)

log = logging.getLogger(__name__)

__all__ = ("GoogleCloudBatchJobRunner",)


class GoogleCloudBatchJobRunner(AsynchronousJobRunner):
    """
    Job runner that submits jobs to Google Cloud Batch.
    """

    runner_name = "GoogleCloudBatchJobRunner"

    def __init__(self, app, nworkers, **kwargs):
        """Initialize the Google Cloud Batch job runner."""
        log.debug("Starting GoogleCloudBatchJobRunner.__init__")

        # Define runner parameter specifications
        runner_param_specs = {
            "project_id": dict(map=str, default=None),
            "region": dict(map=str, default="us-central1"),
            "zone": dict(map=str, default=None),
            "service_account_file": dict(map=str, default=None),
            "service_account_email": dict(map=str, default=None),
            "machine_type": dict(map=str, default="n2-standard-4"),
            "boot_disk_size_gb": dict(map=int, default=100),
            "boot_disk_type": dict(map=str, default="pd-standard"),
            "max_retry_count": dict(map=int, default=3),
            "max_run_duration": dict(map=str, default="3600s"),
            "polling_interval": dict(map=int, default=30),
            # Volume configuration (generic format: "server:/remote_path:/mount_path[:ro],...")
            "gcp_batch_volumes": dict(map=str, default=None),
            # Extra docker volume mounts (format: "/host/path:/container/path[:ro],...")
            "docker_extra_volumes": dict(map=str, default=None),
            # Network configuration for NFS access
            "network": dict(map=str, default="default"),
            "subnet": dict(map=str, default="default"),
            # Compute resource configuration (defaults - will be overridden by job requirements)
            "vcpu": dict(map=float, default=1.0),
            "memory_mib": dict(map=int, default=DEFAULT_MEMORY_MIB),
            # Job-specific resource requests (same as Kubernetes runner)
            "requests_cpu": dict(map=str, default=None),
            "requests_memory": dict(map=str, default=None),
            "limits_cpu": dict(map=str, default=None),
            "limits_memory": dict(map=str, default=None),
            # Container execution settings
            "use_container": dict(map=bool, default=True),
            "galaxy_user_id": dict(
                map=str, valid=lambda s: s == "$uid" or isinstance(s, int) or not s or str(s).isdigit(), default=None
            ),
            "galaxy_group_id": dict(
                map=str, valid=lambda s: s == "$gid" or isinstance(s, int) or not s or str(s).isdigit(), default=None
            ),
            # Custom VM image (optional)
            "custom_vm_image": dict(map=str, default=None),
            # Object store fallback (for future use)
            "use_object_store": dict(map=bool, default=False),
            "object_store_path": dict(map=str, default=None),
        }

        kwargs.update({"runner_param_specs": runner_param_specs})
        super().__init__(app, nworkers, **kwargs)

        # Initialize Google Cloud Batch client
        self._init_batch_client()

        log.info(
            "GoogleCloudBatchJobRunner initialized for project: %s",
            self.runner_params.get("project_id", "Not specified"),
        )
        log.debug("Finished GoogleCloudBatchJobRunner.__init__")

    def _init_batch_client(self):
        """Initialize the Google Cloud Batch client."""
        # Set up authentication
        service_account_file = self.runner_params.get("service_account_file")
        if service_account_file:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account_file

        try:
            credentials, project = default()
            self.batch_client = batch_v1.BatchServiceClient(credentials=credentials)
        except Exception as e:
            log.error("Failed to initialize Google Cloud Batch client: %s", e)
            raise

        # Set project ID
        if not self.runner_params.get("project_id"):
            if project:
                self.runner_params["project_id"] = project
            else:
                raise ValueError("Google Cloud project ID not specified and could not be determined from credentials")

        log.info("Google Cloud Batch client initialized successfully")

    def queue_job(self, job_wrapper):
        """Queue a job for execution on Google Cloud Batch."""
        log.debug("Starting queue_job for Galaxy job %s", job_wrapper.get_id_tag())

        # Create AsynchronousJobState
        ajs = AsynchronousJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper,
            job_destination=job_wrapper.job_destination,
        )

        # Create required output files
        with open(ajs.output_file, "w"):
            pass
        with open(ajs.error_file, "w"):
            pass

        # Prepare the job
        if not self.prepare_job(
            job_wrapper,
            include_metadata=False,
            modify_command_for_container=False,
            stream_stdout_stderr=True,
        ):
            log.error("Failed to prepare job %s", job_wrapper.get_id_tag())
            return

        # Generate job script
        script = self.get_job_file(
            job_wrapper, exit_code_path=ajs.exit_code_file, shell=job_wrapper.shell, galaxy_virtual_env=None
        )

        try:
            self.write_executable_script(ajs.job_file, script, job_io=job_wrapper.job_io)
        except Exception as e:
            log.error("Failed to write job script for job %s: %s", job_wrapper.get_id_tag(), e)
            job_wrapper.fail("Failed to write job script")
            return

        try:
            # Submit job to Google Cloud Batch
            batch_job_name = self._submit_batch_job(job_wrapper, ajs)

            # Store runner information for tracking if Galaxy restarts
            ajs.job_id = batch_job_name
            job_wrapper.set_external_id(batch_job_name)
            self.monitor_queue.put(ajs)

            log.info("Successfully queued Galaxy job %s as Batch job %s", job_wrapper.get_id_tag(), batch_job_name)

        except Exception as e:
            log.error("Failed to submit job %s to Google Cloud Batch: %s", job_wrapper.get_id_tag(), e)
            job_wrapper.fail(f"Failed to submit job to Google Cloud Batch: {e}")

        log.debug("Finished queue_job for Galaxy job %s", job_wrapper.get_id_tag())

    def _submit_batch_job(self, job_wrapper, ajs) -> str:
        """Submit a job to Google Cloud Batch and return the job name."""
        log.debug("Starting _submit_batch_job for job %s", job_wrapper.get_id_tag())

        # Generate unique job name
        job_name = f"galaxy-job-{int(time.time())}-{os.urandom(4).hex()}"

        # Get job destination parameters
        job_destination = job_wrapper.job_destination
        params = self._get_job_params(job_destination)

        # Create the batch job specification
        batch_job = self._create_batch_job_spec(job_wrapper, ajs, params)

        # Submit the job
        request = batch_v1.CreateJobRequest()
        request.parent = f"projects/{params['project_id']}/locations/{params['region']}"
        request.job_id = job_name
        request.job = batch_job

        # Write job parameters and request to JSON files for debugging
        try:
            self._write_debug_files(job_wrapper, ajs, params, request, job_name)
        except Exception as e:
            log.warning("Failed to write debug files for job %s: %s", job_wrapper.get_id_tag(), e)

        try:
            operation = self.batch_client.create_job(request=request)
            log.info("Submitted Batch job %s, operation: %s", job_name, operation.name)
            return job_name
        except Exception as e:
            log.error("Failed to create Batch job: %s", e)
            raise

    def _get_job_params(self, job_destination) -> Dict[str, Any]:
        """Extract job parameters from destination and runner configuration."""
        log.debug("Starting _get_job_params")
        params = {}

        # Copy from runner params with destination overrides
        for key in [
            "project_id",
            "region",
            "zone",
            "machine_type",
            "boot_disk_size_gb",
            "boot_disk_type",
            "max_retry_count",
            "max_run_duration",
            "gcp_batch_volumes",
            "docker_extra_volumes",
            "network",
            "subnet",
            "vcpu",
            "memory_mib",
            "use_container",
            "galaxy_user_id",
            "galaxy_group_id",
            "custom_vm_image",
            "use_object_store",
            "object_store_path",
            "service_account_email",
        ]:
            params[key] = job_destination.params.get(key, self.runner_params.get(key))

        log.debug("Finished _get_job_params")
        return params

    def _create_batch_job_spec(self, job_wrapper, ajs, params):
        """Create a Google Cloud Batch job specification."""
        log.debug("Starting _create_batch_job_spec for job %s", job_wrapper.get_id_tag())

        # Get container image from Galaxy's container finder
        container_image = self._get_container_image(ajs.job_wrapper)
        log.debug("Using container image: %s for job %s", container_image, job_wrapper.get_id_tag())

        # Get compute resources first so we can pass them to script creation
        cpu_milli, memory_mib = self._get_job_resources(job_wrapper, params)

        # Create the execution script based on whether we use containers or not
        if params.get("use_container", True):
            execution_script = self._create_container_execution_script(
                job_wrapper, ajs, params, container_image, cpu_milli, memory_mib
            )
        else:
            execution_script = self._create_direct_execution_script(job_wrapper, ajs, params, cpu_milli, memory_mib)

        # Create runnable with script execution
        runnable = batch_v1.Runnable()
        runnable.script = batch_v1.Runnable.Script()
        runnable.script.text = execution_script

        # Create task specification
        task_spec = batch_v1.TaskSpec()
        task_spec.runnables = [runnable]
        task_spec.max_retry_count = params["max_retry_count"]
        task_spec.max_run_duration = params["max_run_duration"]

        # Set compute resources
        compute_resource = batch_v1.ComputeResource()
        compute_resource.cpu_milli = cpu_milli
        compute_resource.memory_mib = memory_mib
        task_spec.compute_resource = compute_resource

        log.debug(
            "Configured compute resources for job %s: %d mCPU, %d MiB memory",
            job_wrapper.get_id_tag(),
            cpu_milli,
            memory_mib,
        )

        # Configure NFS volumes from gcp_batch_volumes parameter
        volumes_param = params.get("gcp_batch_volumes")
        parsed_volumes = parse_volumes_param(volumes_param) if volumes_param else []

        if parsed_volumes:
            batch_volumes = []
            for vol in parsed_volumes:
                volume = batch_v1.Volume()
                volume.nfs = batch_v1.NFS()
                volume.nfs.server = vol["server"]
                volume.nfs.remote_path = vol["remote_path"]
                volume.mount_path = vol["mount_path"]
                batch_volumes.append(volume)
                log.debug(
                    "Configured NFS volume: %s:%s -> %s for job %s",
                    vol["server"],
                    vol["remote_path"],
                    vol["mount_path"],
                    job_wrapper.get_id_tag(),
                )
            task_spec.volumes = batch_volumes

        # Create task group
        task_group = batch_v1.TaskGroup()
        task_group.task_count = 1
        task_group.task_spec = task_spec

        # Create allocation policy
        allocation_policy = batch_v1.AllocationPolicy()

        # Configure network for NFS access (required when using NFS volumes)
        if parsed_volumes:
            network_interface = batch_v1.AllocationPolicy.NetworkInterface()
            network_interface.network = f"global/networks/{params.get('network', 'default')}"
            network_interface.subnetwork = f"regions/{params['region']}/subnetworks/{params.get('subnet', 'default')}"

            network_policy = batch_v1.AllocationPolicy.NetworkPolicy()
            network_policy.network_interfaces = [network_interface]
            allocation_policy.network = network_policy
            log.debug(
                "Configured network for NFS access: %s/%s for job %s",
                params.get("network", "default"),
                params.get("subnet", "default"),
                job_wrapper.get_id_tag(),
            )

        # Configure instance
        instance_template = batch_v1.AllocationPolicy.InstancePolicyOrTemplate()
        instance_policy = batch_v1.AllocationPolicy.InstancePolicy()
        instance_policy.machine_type = params["machine_type"]

        # Use custom VM image if specified
        if params.get("custom_vm_image"):
            instance_policy.boot_disk = batch_v1.AllocationPolicy.Disk()
            instance_policy.boot_disk.image = params["custom_vm_image"]
            instance_policy.boot_disk.size_gb = params["boot_disk_size_gb"]
            instance_policy.boot_disk.type_ = params["boot_disk_type"]
            log.debug("Using custom VM image: %s for job %s", params["custom_vm_image"], job_wrapper.get_id_tag())
        else:
            # Configure standard boot disk
            disk = batch_v1.AllocationPolicy.Disk()
            disk.size_gb = params["boot_disk_size_gb"]
            disk.type_ = params["boot_disk_type"]
            instance_policy.boot_disk = disk

        instance_template.policy = instance_policy
        allocation_policy.instances = [instance_template]

        # Configure service account for job execution
        service_account_email = params.get("service_account_email")
        if service_account_email:
            service_account = batch_v1.ServiceAccount()
            service_account.email = service_account_email
            allocation_policy.service_account = service_account
            log.debug("Configured service account: %s for job %s", service_account_email, job_wrapper.get_id_tag())
        else:
            log.warning(
                "No service account email specified for job %s - using default compute service account",
                job_wrapper.get_id_tag(),
            )

        # Create job
        job = batch_v1.Job()
        job.task_groups = [task_group]
        job.allocation_policy = allocation_policy

        # Configure logging
        job.logs_policy = batch_v1.LogsPolicy()
        job.logs_policy.destination = batch_v1.LogsPolicy.Destination.CLOUD_LOGGING

        # Set labels for tracking
        job.labels = {
            "galaxy-job-id": str(job_wrapper.job_id),
            "galaxy-tool-id": sanitize_label_value(job_wrapper.tool.id if job_wrapper.tool else "unknown"),
            "galaxy-runner": "gcp-batch",
            "galaxy-handler": sanitize_label_value(self.app.config.server_name),
        }

        log.debug("Finished _create_batch_job_spec for job %s", job_wrapper.get_id_tag())
        return job

    def _get_container_image(self, job_wrapper):
        """Get the container image using Galaxy's container finder.

        Uses Galaxy's standard container resolution system. Tools must have
        container requirements configured for containerized execution.
        """
        # Use Galaxy's container finder system (same approach as Kubernetes runner)
        container = self._find_container(job_wrapper)
        if container and hasattr(container, "container_id") and container.container_id:
            log.info(
                "Using tool-specific container: %s for job %s",
                container.container_id,
                job_wrapper.get_id_tag(),
            )
            return container.container_id

        raise ValueError(
            f"No container image found for job {job_wrapper.get_id_tag()}. "
            "Ensure tool has container requirements configured."
        )

    def _get_job_resources(self, job_wrapper, params):
        """
        Extract CPU and memory requirements from job wrapper and return as GCP Batch format.
        Returns tuple of (cpu_milli, memory_mib).
        """
        # Get job destination parameters
        job_destination = job_wrapper.job_destination

        # Determine CPU requirements (in milli-cores)
        cpu_milli = self._get_cpu_milli(job_destination, params)

        # Determine memory requirements (in MiB)
        memory_mib = self._get_memory_mib(job_destination, params)

        log.debug(
            "Job %s resource requirements: %.1f CPU cores (%d mCPU), %d MiB memory",
            job_wrapper.get_id_tag(),
            cpu_milli / 1000.0,
            cpu_milli,
            memory_mib,
        )

        return cpu_milli, memory_mib

    def _get_cpu_milli(self, job_destination, params):
        """Get CPU requirements in milli-cores (1000 = 1 vCPU)."""
        # Check for job-specific CPU requests (highest priority)
        if "requests_cpu" in job_destination.params:
            cpu_str = job_destination.params["requests_cpu"]
            return convert_cpu_to_milli(cpu_str)

        # Check for job-specific CPU limits
        if "limits_cpu" in job_destination.params:
            cpu_str = job_destination.params["limits_cpu"]
            return convert_cpu_to_milli(cpu_str)

        # Fall back to configured default
        default_vcpu = float(params.get("vcpu", 1.0))
        return int(default_vcpu * 1000)

    def _get_memory_mib(self, job_destination, params):
        """Get memory requirements in MiB."""
        # Check for job-specific memory requests (highest priority)
        if "requests_memory" in job_destination.params:
            memory_str = job_destination.params["requests_memory"]
            return convert_memory_to_mib(memory_str)

        # Check for job-specific memory limits
        if "limits_memory" in job_destination.params:
            memory_str = job_destination.params["limits_memory"]
            return convert_memory_to_mib(memory_str)

        # Fall back to configured default
        return int(params.get("memory_mib", DEFAULT_MEMORY_MIB))

    def _create_container_execution_script(self, job_wrapper, ajs, params, container_image, cpu_milli, memory_mib):
        """Create a script that runs the Galaxy job inside a container with volume mounts."""
        # Parse volumes from gcp_batch_volumes parameter
        volumes_param = params.get("gcp_batch_volumes")
        parsed_volumes = parse_volumes_param(volumes_param) if volumes_param else []

        # Get the primary NFS volume (first one) for script template
        if parsed_volumes:
            primary_volume = parsed_volumes[0]
            nfs_server = primary_volume["server"]
            nfs_path = primary_volume["remote_path"]
            nfs_mount_path = primary_volume["mount_path"]
        else:
            # Fallback defaults if no volumes configured
            nfs_server = "127.0.0.1"
            nfs_path = DEFAULT_NFS_PATH
            nfs_mount_path = DEFAULT_NFS_MOUNT_PATH

        # Build Docker volume arguments from docker_extra_volumes parameter
        docker_volumes_param = params.get("docker_extra_volumes")
        if docker_volumes_param:
            docker_volume_args = parse_docker_volumes_param(docker_volumes_param)
        else:
            # Default to CVMFS mount if no extra volumes specified
            docker_volume_args = DEFAULT_CVMFS_DOCKER_VOLUME

        # Build docker user flag only if user/group IDs are configured
        user_id = params.get("galaxy_user_id")
        group_id = params.get("galaxy_group_id")
        if user_id and group_id:
            docker_user_flag = f"--user {user_id}:{group_id}"
        elif user_id:
            docker_user_flag = f"--user {user_id}"
        else:
            docker_user_flag = ""

        # Compute galaxy_slots from allocated CPU (at least 1 slot)
        galaxy_slots = max(1, int(cpu_milli / 1000))

        template_params = {
            "job_id_tag": job_wrapper.get_id_tag(),
            "tool_id": job_wrapper.tool.id if job_wrapper.tool else "unknown",
            "container_image": container_image,
            "nfs_server": nfs_server,
            "nfs_path": nfs_path,
            "nfs_mount_path": nfs_mount_path,
            "job_file": ajs.job_file,
            "galaxy_slots": galaxy_slots,
            "galaxy_memory_mb": memory_mib,
            "docker_user_flag": docker_user_flag,
            "docker_volume_args": docker_volume_args,
        }

        return CONTAINER_SCRIPT_TEMPLATE.substitute(template_params)

    def _create_direct_execution_script(self, job_wrapper, ajs, params, cpu_milli, memory_mib):
        """Create a script that runs the Galaxy job directly on the VM (without container)."""
        # Parse volumes from gcp_batch_volumes parameter
        volumes_param = params.get("gcp_batch_volumes")
        parsed_volumes = parse_volumes_param(volumes_param) if volumes_param else []

        # Get the primary NFS mount path (first volume) for script template
        if parsed_volumes:
            nfs_mount_path = parsed_volumes[0]["mount_path"]
        else:
            nfs_mount_path = DEFAULT_NFS_MOUNT_PATH

        # Compute galaxy_slots from allocated CPU (at least 1 slot)
        galaxy_slots = max(1, int(cpu_milli / 1000))

        template_params = {
            "job_id_tag": job_wrapper.get_id_tag(),
            "tool_id": job_wrapper.tool.id if job_wrapper.tool else "unknown",
            "nfs_mount_path": nfs_mount_path,
            "job_file": ajs.job_file,
            "galaxy_slots": galaxy_slots,
            "galaxy_memory_mb": memory_mib,
        }

        return DIRECT_SCRIPT_TEMPLATE.substitute(template_params)

    def _write_debug_files(self, job_wrapper, ajs, params, request, job_name):
        """Write job parameters and request object to JSON files for debugging."""
        log.debug("Starting _write_debug_files for job %s", job_wrapper.get_id_tag())

        working_dir = ajs.job_wrapper.working_directory

        # Write job parameters to JSON
        params_file = os.path.join(working_dir, "gcp_batch_job_params.json")
        params_data = {
            "galaxy_job_id": job_wrapper.job_id,
            "galaxy_tool_id": job_wrapper.tool.id if job_wrapper.tool else None,
            "galaxy_tool_version": job_wrapper.tool.version if job_wrapper.tool else None,
            "batch_job_name": job_name,
            "timestamp": time.time(),
            "parameters": params,
            "runner_params": dict(self.runner_params),
            "job_destination": {
                "id": job_wrapper.job_destination.id,
                "tags": job_wrapper.job_destination.tags,
                "params": dict(job_wrapper.job_destination.params),
            },
        }

        with open(params_file, "w") as f:
            json.dump(params_data, f, indent=2, default=str)
        log.debug("Wrote job parameters to %s", params_file)

        # Convert the request object to a JSON-serializable format
        try:
            # Create a simplified representation of the request
            request_data = {
                "parent": request.parent,
                "job_id": request.job_id,
                "job": {"labels": dict(request.job.labels) if request.job.labels else {}, "task_groups": []},
            }

            # Add task group information
            for tg in request.job.task_groups:
                task_group_data = {
                    "task_count": tg.task_count,
                    "task_spec": {
                        "max_retry_count": tg.task_spec.max_retry_count,
                        "max_run_duration": tg.task_spec.max_run_duration,
                        "compute_resource": (
                            {
                                "cpu_milli": tg.task_spec.compute_resource.cpu_milli,
                                "memory_mib": tg.task_spec.compute_resource.memory_mib,
                            }
                            if tg.task_spec.compute_resource
                            else None
                        ),
                        "runnables": [],
                    },
                }

                # Add runnable information
                for runnable in tg.task_spec.runnables:
                    runnable_data = {}
                    if runnable.container:
                        runnable_data["container"] = {
                            "image_uri": runnable.container.image_uri,
                            "commands": list(runnable.container.commands) if runnable.container.commands else [],
                        }
                    task_group_data["task_spec"]["runnables"].append(runnable_data)

                request_data["job"]["task_groups"].append(task_group_data)

            # Add allocation policy
            if request.job.allocation_policy:
                ap = request.job.allocation_policy
                request_data["job"]["allocation_policy"] = {"instances": []}

                for instance in ap.instances:
                    instance_data = {}
                    if instance.policy:
                        instance_data["policy"] = {"machine_type": instance.policy.machine_type}
                        if instance.policy.boot_disk:
                            instance_data["policy"]["boot_disk"] = {
                                "size_gb": instance.policy.boot_disk.size_gb,
                                "type": instance.policy.boot_disk.type_,
                            }
                    request_data["job"]["allocation_policy"]["instances"].append(instance_data)

            # Write request object to JSON
            request_file = os.path.join(working_dir, "gcp_batch_job_request.json")
            with open(request_file, "w") as f:
                json.dump(request_data, f, indent=2, default=str)
            log.debug("Wrote job request to %s", request_file)

        except Exception as e:
            log.warning("Failed to serialize request object for job %s: %s", job_wrapper.get_id_tag(), e)
            # Write a minimal request file with basic info
            minimal_request = {
                "parent": request.parent,
                "job_id": request.job_id,
                "error": f"Failed to serialize full request: {e}",
            }
            request_file = os.path.join(working_dir, "gcp_batch_job_request.json")
            with open(request_file, "w") as f:
                json.dump(minimal_request, f, indent=2, default=str)
            log.debug("Wrote minimal job request to %s", request_file)

        log.debug("Finished _write_debug_files for job %s", job_wrapper.get_id_tag())

    def check_watched_item(self, job_state):
        """Check the status of a job running on Google Cloud Batch."""
        log.debug("Starting check_watched_item for job %s", job_state.job_id)

        batch_job_name = job_state.job_id
        try:
            # Get job status from Google Cloud Batch
            job_path = f"projects/{self.runner_params['project_id']}/locations/{self.runner_params['region']}/jobs/{batch_job_name}"
            batch_job = self.batch_client.get_job(name=job_path)

            # Process job status
            job_status = batch_job.status.state
            log.debug("Batch job %s status: %s", batch_job_name, job_status.name)

            if job_status == batch_v1.JobStatus.State.SUCCEEDED:
                log.info("Batch job %s completed successfully", batch_job_name)
                job_state.running = False
                job_state.job_wrapper.change_state(model.Job.states.OK)
                self.mark_as_finished(job_state)
                log.debug("Finished check_watched_item for job %s (completed successfully)", job_state.job_id)
                return None  # Remove from monitoring

            elif job_status == batch_v1.JobStatus.State.FAILED:
                log.warning("Batch job %s failed", batch_job_name)
                job_state.running = False
                job_state.job_wrapper.change_state(model.Job.states.ERROR)
                self.mark_as_failed(job_state)
                log.debug("Finished check_watched_item for job %s (failed)", job_state.job_id)
                return None  # Remove from monitoring

            elif job_status in [
                batch_v1.JobStatus.State.RUNNING,
                batch_v1.JobStatus.State.QUEUED,
                batch_v1.JobStatus.State.SCHEDULED,
            ]:
                log.debug("Batch job %s is %s", batch_job_name, job_status.name)
                job_state.running = True
                if job_status == batch_v1.JobStatus.State.RUNNING:
                    job_state.job_wrapper.change_state(model.Job.states.RUNNING)
                elif job_status in [batch_v1.JobStatus.State.SCHEDULED, batch_v1.JobStatus.State.QUEUED]:
                    job_state.job_wrapper.change_state(model.Job.states.QUEUED)
                log.debug("Finished check_watched_item for job %s (still running/queued/scheduled)", job_state.job_id)
                return job_state  # Continue monitoring

            else:
                log.warning("Batch job %s in unexpected state: %s", batch_job_name, job_status.name)
                return job_state  # Continue monitoring

        except gcp_exceptions.NotFound:
            log.error("Batch job %s not found", batch_job_name)
            job_state.running = False
            job_state.job_wrapper.change_state(model.Job.states.ERROR)
            self.mark_as_failed(job_state)
            return None

        except Exception as e:
            log.error("Error checking status of Batch job %s: %s", batch_job_name, e)
            # Return job_state to continue monitoring - might be temporary error
            return job_state

    def stop_job(self, job_wrapper):
        """Stop a job running on Google Cloud Batch."""
        job = job_wrapper.get_job()
        log.debug("Starting stop_job for job %s", job.id)

        batch_job_name = job.get_job_runner_external_id()
        if batch_job_name:
            try:
                job_path = f"projects/{self.runner_params['project_id']}/locations/{self.runner_params['region']}/jobs/{batch_job_name}"
                self.batch_client.delete_job(name=job_path)
                log.info("Cancelled Batch job %s", batch_job_name)
            except Exception as e:
                log.error("Failed to cancel Batch job %s: %s", batch_job_name, e)
        else:
            log.warning("Could not stop job %s - no external job ID", job.id)

        log.debug("Finished stop_job for job %s", job.id)

    def recover(self, job, job_wrapper):
        """Recover jobs that were running when Galaxy restarted."""
        log.debug("Starting recover for job %s", job.id)
        log.info("Recovering job %s", job.id)

        # Create AsynchronousJobState for recovery
        ajs = AsynchronousJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper,
            job_destination=job_wrapper.job_destination,
        )

        # Set the external job ID
        ajs.job_id = job.get_job_runner_external_id()

        if ajs.job_id:
            # Add to monitoring if job was running
            if job.state in [model.Job.states.RUNNING, model.Job.states.QUEUED]:
                ajs.running = job.state == model.Job.states.RUNNING
                self.monitor_queue.put(ajs)
                log.info("Recovered job %s for monitoring", job.id)
        else:
            log.warning("Could not recover job %s - no external job ID", job.id)

        log.debug("Finished recover for job %s", job.id)

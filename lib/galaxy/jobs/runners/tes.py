"""
Job control via TES.
"""
import logging
import os
from re import escape, findall

import requests
import shlex

from galaxy import model
from galaxy.jobs import JobWrapper
from galaxy.jobs.command_factory import build_command
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)
from galaxy.util import asbool

log = logging.getLogger(__name__)

__all__ = ('TESJobRunner', )

GENERIC_REMOTE_ERROR = "Failed to communicate with remote job server."
FAILED_REMOTE_ERROR = "Remote job server indicated a problem running or monitoring the job."
LOST_REMOTE_ERROR = "Remote job server could not determine the job's state."

DEFAULT_GALAXY_URL = "http://localhost:8080/"


class TESJobState(AsynchronousJobState):
    def __init__(self, **kwargs):
        """
        Encapsulates state related to a job.
        """
        super().__init__(**kwargs)
        self.user_log = None
        self.user_log_size = 0
        self.cleanup_file_attributes = ['output_file', 'error_file', 'exit_code_file']


class TESJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "TESJobRunner"

    def __init__(self, app, nworkers, **kwargs):
        """
            Initialize this job runner and start the monitor thread
        """
        super().__init__(app, nworkers, **kwargs)
        self.container_workdir = "/tmp"
        if(hasattr(app.config, "galaxy_infrastructure_url")):
            self.galaxy_url = f"{app.config.galaxy_infrastructure_url.rstrip('/')}/"
        else:
            raise Exception("Galaxy URL isn't specified")

        self.running_states = ["RUNNING", "INITIALIZING", "QUEUED", "PAUSED"]
        self.complete_states = ["COMPLETE"]
        self.error_states = ["EXECUTOR_ERROR", "SYSTEM_ERROR", "CANCELED", "UNKNOWN"]
        self.cancel_state = ["CANCELED"]

        self._init_monitor_thread()
        self._init_worker_threads()

    def _send_task(self, master_addr: str, task: dict):
        """
            Send job-script to TES
        """
        log.debug("Sending job script to TES Server")
        url = f"{master_addr}/v1/tasks"
        try:
            req = requests.post(url, json=task)
            try:
                job_id = req.json()["id"]
                return job_id
            except KeyError:
                log.error(f"TES Server failed to accept the job {req.json()}")
        except requests.exceptions:
            log.error(f"{GENERIC_REMOTE_ERROR} on URL {master_addr}")

    def _get_job(self, master_addr: str, job_id: str, view: str = "MINIMAL"):
        """
            Get Job Status from TES Server
        """
        log.debug(f"Getting status for job id {job_id}")
        url = f"{master_addr}/v1/tasks/{str(job_id)}"
        try:
            req = requests.get(url, params={'view': view})
            return req.json()
        except requests.exceptions:
            log.error(f"{LOST_REMOTE_ERROR} for job id {job_id}")

    def _cancel_job(self, master_addr: str, job_id: str):
        """
            Cancel the Job on TES Server
        """
        log.debug(f"Cancelling the job id {job_id}")
        url = f"{master_addr}/v1/tasks/{job_id}:cancel"
        try:
            requests.post(url)
        except requests.exceptions:
            log.error(f"{GENERIC_REMOTE_ERROR} for cancellation of job id {job_id}")

    def get_upload_path(self, job_id: str, env=None):
        """
            For getting upload URL for staging in the files
        """
        if env is None:
            env = []

        encoded_job_id = self.app.security.encode_id(job_id)
        job_key = self.app.security.encode_id(job_id, kind="jobs_files")
        endpoint_base = "%sapi/jobs/%s/files?job_key=%s"

        if self.app.config.nginx_upload_job_files_path:
            endpoint_base = "%s" + \
                            self.app.config.nginx_upload_job_files_path + \
                            "?job_id=%s&job_key=%s"

        files_endpoint = endpoint_base % (
            self.galaxy_url,
            encoded_job_id,
            job_key
        )

        get_client_kwds = dict(
            job_id=str(job_id),
            files_endpoint=files_endpoint,
            env=env
        )
        return get_client_kwds

    def find_referenced_subfiles(self, directory: str, command_line: str, extra_files: list):
        """
        Return list of files below specified `directory` in job inputs. Could
        use more sophisticated logic (match quotes to handle spaces, handle
        subdirectories, etc...).
        **Parameters**
        directory : str
            Full path to directory to search.
        """
        if directory is None:
            return []

        pattern = r'''[\'\"]?(%s%s[^\s\'\"]+)[\'\"]?''' % (escape(directory), escape(os.sep))
        return self.find_pattern_references(pattern, command_line, extra_files)

    def _read(self, path: str):
        """
        Utility method to quickly read small files (config files and tool
        wrappers) into memory as bytes.
        """
        input = open(path, "rb", encoding="utf-8")
        try:
            return input.read()
        finally:
            input.close()

    def __items(self, command_line: str, extra_files: list):
        """
        Utility method to form the list in required format
        for getting input files using regex
        """
        items = [command_line]
        config_files = {}
        for config_file in extra_files or []:
            config_contents = self._read(config_file)
            config_files[config_file] = config_contents
        items.extend(config_files.values())
        return items

    def find_pattern_references(self, pattern: str, command_line: str, extra_files: list):
        """
        Finding the list of referenced file, using regex
        """
        referenced_files = set()
        for input_contents in self.__items(command_line, extra_files):
            referenced_files.update(findall(pattern, input_contents))
        return list(referenced_files)

    def file_creation_executor(self, mounted_dir: str, docker_image: str, work_dir: str):
        """
        Returns the executor for creation of files
        """
        file_executor = {
            "workdir": mounted_dir,
            "image": docker_image,
            "command": ["/bin/bash", os.path.join(work_dir, 'createfiles.sh')]
        }
        return file_executor

    def job_executor(self, mounted_dir: str, remote_image: str, command_line: str, env: dict):
        """
        Returns the executor for executing jobs
        """
        job_executor = {
            "workdir": mounted_dir,
            "image": remote_image,
            "command": shlex.split(command_line),
            "env": env
        }
        return job_executor

    def file_staging_out_executor(self, mounted_dir: str, docker_image: str, command: list):
        """
        Returns the executor for staging out of the files
        """
        staging_out_executor = {
            "workdir": mounted_dir,
            "image": docker_image,
            "command": command
        }
        return staging_out_executor

    def base_job_script(self, mounted_dir: str, work_dir: str, output_files: list, description: str):
        """
        Retruns the basic structure for job-script
        """
        execution_script = {
            "name": "Galaxy Job Execution",
            "description": description,
            "inputs": [
                {
                    "path": os.path.join(work_dir, 'createfiles.sh'),
                    "content": self.output_file_gen_script(output_files),
                }],
            "executors": [],
            "volumes": [mounted_dir]
        }

        return execution_script

    def output_file_gen_script(self, output_files: list):
        """
            Generates shell script for generating output files in container
        """
        script = []

        for file in output_files:
            dir_name = os.path.split(file)[0]
            script.extend(['mkdir', '-p', dir_name, '&&', 'touch', file, '&&'])

        script[-1] = '\n'
        return ' '.join(script)

    def staging_out_command(self, script_path: str, output_files: list, api_url: str, work_dir: str):
        """
            Generates command for staging out of files
        """
        command = ["python", script_path, api_url, work_dir]

        for file in output_files:
            command.append(file)

        return command

    def env_variables(self, job_wrapper: JobWrapper):
        """
            Get environment variables from job_wrapper
        """
        env_vars = {}
        for variable in job_wrapper.environment_variables:
            env_vars[variable['name']] = variable['value']

        for variable in job_wrapper.job_destination.env:
            env_vars[variable['name']] = variable['value']

        env_vars["_GALAXY_JOB_TMP_DIR"] = self.container_workdir
        env_vars["_GALAXY_JOB_HOME_DIR"] = self.container_workdir
        return env_vars

    def input_url(self, api_url: str, path: str):
        """
            Get URL for path
        """
        file_link = f"{api_url}&path={path}"
        return file_link

    def input_descriptors(self, api_url: str, input_paths: list, type: str = "FILE"):
        """
            Get Input Descriptor for Jobfile
        """
        input_description = []

        for path in input_paths:
            input_description.append({
                "url": self.input_url(api_url, path),
                "path": path,
                "type": type
            })
        return input_description

    def get_job_directory_files(self, work_dir: str):
        """
        Get path for all the files from work directory
        """
        paths = []
        for root, _, files in os.walk(work_dir):
            for file in files:
                paths.append(os.path.join(root, file))

        return paths

    def get_docker_image(self, job_wrapper: JobWrapper):
        """
            For getting the docker image to be used
        """
        remote_container = self._find_container(job_wrapper)
        remote_image = None
        staging_docker_image = None

        if(hasattr(job_wrapper.job_destination, "params")):
            if("default_docker_image" in job_wrapper.job_destination.params):
                remote_image = job_wrapper.job_destination.params.get("default_docker_image")

        if(hasattr(job_wrapper.job_destination, "params")):
            if("staging_docker_image" in job_wrapper.job_destination.params):
                staging_docker_image = job_wrapper.job_destination.params.get("staging_docker_image")

            else:
                staging_docker_image = remote_image

        if(hasattr(remote_container, "container_id")):
            remote_image = remote_container.container_id

        if(staging_docker_image is None):
            staging_docker_image = remote_image

        if(remote_image is None):
            raise Exception("default_docker_image not specified")
        else:
            return remote_image, staging_docker_image

    def build_script(self, job_wrapper: JobWrapper, client_args: dict):
        """
        Returns the Job script with required configurations of the job
        """
        tool_dir = job_wrapper.tool.tool_dir
        work_dir = job_wrapper.working_directory
        object_store_path = job_wrapper.object_store.file_path
        mount_path = os.path.commonprefix([work_dir, object_store_path])
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "util/file-staging.py")

        input_files = self.__get_inputs(job_wrapper)
        output_files = self.get_output_files(job_wrapper)
        extra_files = job_wrapper.extra_filenames
        tool_files = self.find_referenced_subfiles(tool_dir, job_wrapper.command_line, extra_files)

        remote_image, staging_out_image = self.get_docker_image(job_wrapper)

        command_line = build_command(self,
                job_wrapper=job_wrapper,
                include_metadata=False,
                create_tool_working_directory=False,
                include_work_dir_outputs=False,
                remote_job_directory=job_wrapper.working_directory)

        env_var = self.env_variables(job_wrapper)
        staging_out_command = self.staging_out_command(script_path, output_files, client_args['files_endpoint'], job_wrapper.working_directory)

        job_script = self.base_job_script(mount_path, work_dir, output_files, job_wrapper.tool.description)

        job_script["inputs"].extend(self.input_descriptors(client_args['files_endpoint'], [script_path]))
        job_script["inputs"].extend(self.input_descriptors(client_args['files_endpoint'], tool_files))
        job_script["inputs"].extend(self.input_descriptors(client_args['files_endpoint'], self.get_job_directory_files(work_dir)))
        job_script["inputs"].extend(self.input_descriptors(client_args['files_endpoint'], input_files))

        job_script["executors"].append(self.file_creation_executor(mount_path, staging_out_image, work_dir))
        job_script["executors"].append(self.job_executor(mount_path, remote_image, command_line, env_var))
        job_script["executors"].append(self.file_staging_out_executor(mount_path, staging_out_image, staging_out_command))

        return job_script

    def __get_inputs(self, job_wrapper: JobWrapper):
        """Returns the list about the details of input files."""

        input_files = []

        for input_dataset_wrapper in job_wrapper.get_input_paths():
            path = str(input_dataset_wrapper)
            input_files.append(path)

        return input_files

    def queue_job(self, job_wrapper: JobWrapper):
        """Submit the job to TES."""

        log.debug(f"Starting queue_job for job {job_wrapper.get_id_tag()}")

        include_metadata = asbool(job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
        if not self.prepare_job(job_wrapper, include_metadata=include_metadata):
            return

        job_id = job_wrapper.job_id
        if hasattr(job_wrapper, 'task_id'):
            job_id = f"{job_id}_{job_wrapper.task_id}"

        client_args = self.get_upload_path(job_id)
        job_destination = job_wrapper.job_destination
        galaxy_id_tag = job_wrapper.get_id_tag()
        master_addr = job_destination.params.get("tes_master_addr")

        job_script = self.build_script(job_wrapper, client_args)
        job_id = self._send_task(master_addr, job_script)

        if(job_id is None):
            log.debug(f"Unable to set job on TES instance {master_addr}")
            return

        job_state = TESJobState(
            job_id=job_id,
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper
        )

        log.info("(%s) queued as %s" % (galaxy_id_tag, job_id))
        job_wrapper.set_job_destination(job_destination, job_id)
        self.monitor_job(job_state)

    def get_output_files(self, job_wrapper: JobWrapper):
        """
        Utility for getting list of Output Files
        """
        output_paths = job_wrapper.get_output_fnames()
        return [str(o) for o in output_paths]

    def __finish_job(self, data: dict, job_wrapper: JobWrapper):
        """
        Utility for finishing job after completion
        """
        stdout = self._concat_job_log(data, 'stdout')
        stderr = self._concat_job_log(data, 'stderr')
        exit_code = self._get_exit_codes(data)

        job_metrics_directory = os.path.join(job_wrapper.working_directory, "metadata")
        try:
            job_wrapper.finish(
                stdout,
                stderr,
                exit_code,
                job_metrics_directory=job_metrics_directory,
            )
        except Exception:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

    def _concat_job_log(self, data: dict, key: str):
        """"
        Utility for concatination required job logs
        """
        logs_data = data.get('logs')
        log_lines = []
        for log in logs_data:
            if('logs' in log):
                for log_output in log.get('logs'):
                    log_line = log_output.get(key)
                    if log_line is not None:
                        log_lines.append(log_line)
        return "\n".join(log_lines)

    def _get_exit_codes(self, data: dict):
        """"
        Utility for getting out exit code of the job
        """
        if(data['state'] == "COMPLETE"):
            return 0
        else:
            return 1

    def check_watched_item(self, job_state: TESJobState):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        job_id = job_state.job_id
        galaxy_id_tag = job_state.job_wrapper.get_id_tag()
        master_addr = job_state.job_wrapper.job_destination.params.get("tes_master_addr")

        data = self._get_job(master_addr, job_id, "FULL")
        state = data['state']

        job_running = state in self.running_states
        job_complete = state in self.complete_states
        job_failed = state in self.error_states
        job_cancel = state in self.cancel_state

        if job_running and job_state.running:
            return job_state

        if job_running and not job_state.running:
            log.debug("(%s/%s) job is now running" % (galaxy_id_tag, job_id))
            job_state.job_wrapper.change_state(model.Job.states.RUNNING)
            job_state.running = True
            return job_state

        if not job_running and job_state.running:
            log.debug("(%s/%s) job has stopped running" % (galaxy_id_tag, job_id))
            if(job_cancel):
                job_state.job_wrapper.change_state(model.Job.states.DELETED)
                job_state.running = False
                self.__finish_job(data, job_state.job_wrapper)
                return

        if job_complete:
            if job_state.job_wrapper.get_state() != model.Job.states.DELETED:
                external_metadata = asbool(job_state.job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
                if external_metadata:
                    self._handle_metadata_externally(job_state.job_wrapper, resolve_requirements=True)

                self.__finish_job(data, job_state.job_wrapper)
                log.debug("(%s/%s) job has completed" % (galaxy_id_tag, job_id))
            return

        if job_failed:
            log.debug("(%s/%s) job failed" % (galaxy_id_tag, job_id))
            self.__finish_job(data, job_state.job_wrapper)
            return

        return job_state

    def stop_job(self, job_wrapper: JobWrapper):
        """Attempts to delete a task from the task queue"""
        job = job_wrapper.get_job()

        job_id = job.job_runner_external_id
        if job_id is None:
            return

        master_addr = job.destination_params.get('tes_master_addr')
        self._cancel_job(master_addr, job_id)

    def recover(self, job: model.Job, job_wrapper: JobWrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        # TODO Check if we need any changes here
        job_id = job.get_job_runner_external_id()
        galaxy_id_tag = job_wrapper.get_id_tag()
        if job_id is None:
            self.put(job_wrapper)
            return
        job_state = TESJobState(job_wrapper=job_wrapper, files_dir=self.app.config.cluster_files_directory)
        job_state.job_id = str(job_id)
        job_state.command_line = job.get_command_line()
        job_state.job_wrapper = job_wrapper
        job_state.job_destination = job_wrapper.job_destination
        job_state.user_log = os.path.join(self.app.config.cluster_files_directory, 'galaxy_%s.tes.log' % galaxy_id_tag)
        job_state.register_cleanup_file_attribute('user_log')
        if job.state == model.Job.states.RUNNING:
            log.debug("(%s/%s) is still in running state, adding to the DRM queue" % (job.id, job.job_runner_external_id))
            job_state.running = True
            self.monitor_queue.put(job_state)
        elif job.state == model.Job.states.QUEUED:
            log.debug("(%s/%s) is still in DRM queued state, adding to the DRM queue" % (job.id, job.job_runner_external_id))
            job_state.running = False
            self.monitor_queue.put(job_state)

"""
Job control via TES.
"""
import logging
import os
from re import escape, findall
from os import sep
import requests

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)
from galaxy.jobs.command_factory import build_command
from galaxy.util import asbool

log = logging.getLogger(__name__)

__all__ = ('TESJobRunner', )

GENERIC_REMOTE_ERROR = "Failed to communicate with remote job server."
FAILED_REMOTE_ERROR = "Remote job server indicated a problem running or monitoring the job."
LOST_REMOTE_ERROR = "Remote job server could not determine the job's state."

DEFAULT_GALAXY_URL = "http://localhost:8080"


class TESJobState(AsynchronousJobState):
    def __init__(self, **kwargs):
        """
        Encapsulates state related to a job.
        """
        super(TESJobState, self).__init__(**kwargs)
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
        super(TESJobRunner, self).__init__(app, nworkers, **kwargs)
        self.container_workdir = "/tmp"
        self.galaxy_url = "http://localhost:8080/"
        self._init_monitor_thread()
        self._init_worker_threads()

    def _send_task(self, master_addr, task):
        """
            Send job-script to TES
        """
        log.debug(f"Sending job script to TES Server")
        url = f"{master_addr}/v1/tasks"
        try:
            req = requests.post(url, json=task)
            job_id = req.json()["id"]
            return job_id
        except:
            log.error(f"{GENERIC_REMOTE_ERROR} on URL {master_addr}")
            

    def _get_job(self, master_addr, job_id, view = "MINIMAL"):
        """
            Get Job Status from TES Server
        """
        log.debug(f"Getting status for job id {job_id}")
        url = f"{master_addr}/v1/tasks/{str(job_id)}"
        try:
            req = requests.get(url,params={'view' : view})
            return req.json()
        except:
            log.error(f"{LOST_REMOTE_ERROR} for job id {job_id}")


    def _cancel_job(self, master_addr, job_id):
        """
            Cancel the Job on TES Server
        """
        log.debug(f"Cancelling the job id {job_id}")
        url = f"{master_addr}/v1/tasks/{job_id}:cancel"
        try:
            req = requests.post(url)
        except:
            log.error(f"{GENERIC_REMOTE_ERROR} for cancellation of job id {job_id}")


    def get_upload_path(self, job_id, env=None):
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

    def output_names(self):
        # Maybe this should use the path mapper, but the path mapper just uses basenames
        return self.job_wrapper.get_output_basenames()

    def find_referenced_subfiles(self, directory, command_line, extra_files):
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

        pattern = r'''[\'\"]?(%s%s[^\s\'\"]+)[\'\"]?''' % (escape(directory), escape(sep))
        return self.find_pattern_references(pattern, command_line, extra_files)

    def _read(self, path):
        """
        Utility method to quickly read small files (config files and tool
        wrappers) into memory as bytes.
        """
        input = open(path, "r", encoding="utf-8")
        try:
            return input.read()
        finally:
            input.close()

    def __items(self, command_line, extra_files):
        items = [command_line]
        config_files = {}
        for config_file in extra_files or []:
            config_contents = self._read(config_file)
            config_files[config_file] = config_contents
        items.extend(config_files.values())
        return items

    def find_pattern_references(self, pattern, command_line, extra_files):
        referenced_files = set()
        for input_contents in self.__items(command_line, extra_files):
            referenced_files.update(findall(pattern, input_contents))
        return list(referenced_files)

    def __prepare_jobscript(self, job_wrapper, metadata_directory, client_args):
        input_files = self.__get_inputs(job_wrapper)
        work_dir_outputs = self.get_work_dir_outputs(job_wrapper)
        output_files = self.get_output_files(job_wrapper)
        metadata_directory = os.path.join(job_wrapper.working_directory, "metadata")
        metadata_strategy = job_wrapper.get_destination_configuration('metadata_strategy', None)
        config_files = job_wrapper.extra_filenames
        tool_dir = job_wrapper.tool.tool_dir
        tool_names = os.listdir(tool_dir)

        client_inputs_list = self.__get_inputs(job_wrapper)
        commands = job_wrapper.command_line
        from shlex import split
        commands = split(commands)
        other_inputs = job_wrapper.extra_filenames

        remote_container = self._find_container(job_wrapper)
        remote_image = "python"

        if(hasattr(remote_container, "container_id")):
            remote_image = remote_container.container_id


        final_commands = []
        file_creation = []

        command_line = build_command(
                self,
                job_wrapper=job_wrapper,
                include_metadata=False,
                create_tool_working_directory=False,
                include_work_dir_outputs=False,
                remote_job_directory=job_wrapper.working_directory,
            )

        for output_f in output_files:
            head_tail = os.path.split(output_f)
            file_creation.extend(['mkdir', '-p', head_tail[0], '&&',  'touch', output_f, '&&'])

        file_creation[-1] = '\n'
        final_commands.extend(["/bin/bash", client_inputs_list[-1]["paths"]])
        staging_up_command = ["python", "/inputs/staging.py", client_args['files_endpoint']]

        for output_path in output_files:
            staging_up_command.append(output_path)
        
        for output_path in other_inputs:
            staging_up_command.append(output_path)

        file_staging_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "util/file-staging.py")

        referenced_tool_files = self.find_referenced_subfiles(tool_dir, job_wrapper.command_line, other_inputs)
        actual_job_directory = job_wrapper.working_directory
        object_store_path = job_wrapper.object_store.file_path
        common_path = os.path.commonprefix([actual_job_directory, object_store_path])
        execution_script = {
            "name": "Galaxy Job Execution",
            "description": job_wrapper.tool.description,
            "inputs": [
                        {
                            "path": os.path.join(job_wrapper.working_directory, 'createfiles.sh'),
                            "content" : ' '.join(file_creation),
                        }
                    ],
            "outputs": [],
            "executors": [
                {
                    "workdir": common_path,
                    "image": "vipchhabra99/pulsar-lib",
                    "command": ["/bin/bash",os.path.join(job_wrapper.working_directory, 'createfiles.sh')]
                },
                {
                    "workdir": common_path,
                    "image": remote_image,
                    "command": command_line.split(),
                    "env": {}
                },
                {
                    "workdir" : common_path,
                    "image" : "vipchhabra99/pulsar-lib",
                    "command" : staging_up_command
                }
            ],
            "volumes": [common_path]
        }
        


        for input in referenced_tool_files:
            execution_script["inputs"].append({"url": client_args['files_endpoint'] + '&path=' + input, "path": input})

        for root, _ , files in os.walk(job_wrapper.working_directory):
            for file in files:
                execution_script["inputs"].append({"url": client_args['files_endpoint'] + '&path=' + os.path.join(root, file), "path": os.path.join(root, file)})
        
        execution_script["inputs"].append({"url": client_args['files_endpoint'] + '&path=' + file_staging_path, "path": "/inputs/staging.py"})
        for input in client_inputs_list:
            execution_script["inputs"].append({"url": client_args['files_endpoint'] + '&path=' + input["paths"], "path": input["paths"]})

        return execution_script

    def __get_inputs(self, job_wrapper):
        """Returns the list about the details of input files."""

        client_inputs_list = []

        for input_dataset_wrapper in job_wrapper.get_input_paths():
            # str here to resolve false_path if set on a DatasetPath object.
            path = str(input_dataset_wrapper)
            object_store_ref = {
                "paths": path,
                "dataset_id": input_dataset_wrapper.dataset_id,
                "dataset_uuid": str(input_dataset_wrapper.dataset_uuid),
                "object_store_id": input_dataset_wrapper.object_store_id,
            }
            client_inputs_list.append(object_store_ref)

        return client_inputs_list

    def queue_job(self, job_wrapper):
        """Submit the job to TES."""

        log.debug(f"Starting queue_job for job {job_wrapper.get_id_tag()}")

        include_metadata = asbool(job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
        if not self.prepare_job(job_wrapper, include_metadata=include_metadata):
            return

        job_id = job_wrapper.job_id
        if hasattr(job_wrapper, 'task_id'):
            job_id = f"{job_id}_{job_wrapper.task_id}"
        params = job_wrapper.job_destination.params.copy()
        client_args = self.get_upload_path(job_id)
        job_destination = job_wrapper.job_destination
        galaxy_id_tag = job_wrapper.get_id_tag()
        master_addr = job_destination.params.get("tes_master_addr")
        working_directory = job_wrapper.working_directory

        if self.app.config.metadata_strategy == "legacy":
            metadata_directory = job_wrapper.working_directory
        else:
            metadata_directory = os.path.join(job_wrapper.working_directory, "metadata")

        execution_script = self.__prepare_jobscript(job_wrapper, metadata_directory, client_args)

        job_id = self._send_task(master_addr, execution_script)

        job_state = TESJobState(
            job_id=job_id,
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper
        )

        log.info("(%s) queued as %s" % (galaxy_id_tag, job_id))
        job_wrapper.set_job_destination(job_destination, job_id)
        self.monitor_job(job_state)

    def get_output_files(self, job_wrapper):
        output_paths = job_wrapper.get_output_fnames()
        return [str(o) for o in output_paths]   # Force job_path from DatasetPath objects.

    def get_input_files(self, job_wrapper):
        input_paths = job_wrapper.get_input_paths()
        return [str(i) for i in input_paths]

    def __finish_job(self, stdout, stderr, exit_code, job_wrapper):
        
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

    def _concat_job_log(self, data, key):
        s = ''
        try:
            logs_data = data.get('logs')
            for log in logs_data:
                # s += 'Step #{}\n'.format(i)
                actual_log = log.get('logs')
                for log_output in actual_log:
                    try:
                        s += log_output[key] + "\n"
                    except:
                        s += ''
            return s

        except:
            return s

    def _concat_exit_codes(self, data):
        if(data['state'] == "COMPLETE"):
            return '0'

        else:
            return '1'

    def check_watched_item(self, job_state):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        job_id = job_state.job_id
        galaxy_id_tag = job_state.job_wrapper.get_id_tag()
        master_addr = job_state.job_wrapper.job_destination.params.get("tes_master_addr")

        data = self._get_job(master_addr, job_id, "FULL")
        state = data['state']

        running_states = ["RUNNING", "INITIALIZING", "QUEUED", "PAUSED"]
        complete_states = ["COMPLETE"]
        error_states = ["EXECUTOR_ERROR", "SYSTEM_ERROR", "CANCELED", "UNKNOWN"]
        cancel_state = ["CANCELED"]
        
        job_running = state in running_states
        job_complete = state in complete_states
        job_failed = state in error_states
        job_cancel = state in cancel_state

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
                self.__finish_job('', '', 0, job_state.job_wrapper)

        if job_complete:
            if job_state.job_wrapper.get_state() != model.Job.states.DELETED:
                external_metadata = asbool(job_state.job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
                if external_metadata:
                    self._handle_metadata_externally(job_state.job_wrapper, resolve_requirements=True)
                
                stdout = self._concat_job_log(data, 'stdout')
                stderr = self._concat_job_log(data, 'stderr')
                exit_code = self._concat_exit_codes(data)
                self.__finish_job(stdout, stderr, exit_code, job_state.job_wrapper)
                log.debug("(%s/%s) job has completed" % (galaxy_id_tag, job_id))
            return

        if job_failed:
            log.debug("(%s/%s) job failed" % (galaxy_id_tag, job_id))
            stdout = ""
            stderr = self._concat_job_log(data, 'stderr')
            exit_code = 1
            self.__finish_job(stdout, stderr, exit_code, job_state.job_wrapper)
            return

        return job_state

    def stop_job(self, job_wrapper):
        """Attempts to delete a task from the task queue"""
        # TODO: This needs a thorough check why job Id is not coming with job_object
        # and why this is getting called after the job completion in failed case
        job = job_wrapper.get_job()

        job_id = job.job_runner_external_id
        if job_id is None:
            return

        master_addr = job.destination_params.get('tes_master_addr')
        self._cancel_job(master_addr, job_id)

    def recover(self, job, job_wrapper):
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
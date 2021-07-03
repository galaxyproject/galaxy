"""
Job control via TES.
"""
import logging
import os
import json
import shlex
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
FAILED_REMOTE_ERROR = "Remote job server indicated a problem running or monitoring this job."
LOST_REMOTE_ERROR = "Remote job server could not determine this job's state."

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
        """Initialize this job runner and start the monitor thread"""
        super(TESJobRunner, self).__init__(app, nworkers, **kwargs)
        self.container_workdir = "/tmp"
        self.galaxy_url = "http://localhost:8080/"
        # self.tes_url = tes_url
        # self.tes_client = tes.HTTPClient(url=self.tes_url)
        self._init_monitor_thread()
        self._init_worker_threads()

    def _send_task(self, master_addr, task):
        url = master_addr + "/v1/tasks"
        r = requests.post(url, json=task)
        data = r.json()
        job_id = data["id"]
        return job_id

    def _get_job(self, master_addr, job_id):
        url = master_addr + "/v1/tasks/" + str(job_id)
        r = requests.get(url)
        print(r.text)
        return r.json()

    def _cancel_job(self, master_addr, job_id):
        url = master_addr + "/v1/tasks" + str(job_id) + ":cancel"
        r = requests.post(url)

    def get_upload_path(self, job_destination_params, job_id, env=None):
        # Cannot use url_for outside of web thread.
        # files_endpoint = url_for( controller="job_files", job_id=encoded_job_id )
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
        # Turn MutableDict into standard dict for pulsar consumption
        job_destination_params = dict(job_destination_params.items())
        return get_client_kwds, job_destination_params

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

    def __prepare_jobscript(self, job_wrapper):
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
        # script_path = commands[1]
        # final_commands = ["pip", "install", "galaxy-lib"]
        # for cmd in commands:
        #     final_commands.append(cmd)

        # for tool_name in tool_names:
        #     execution_script["inputs"].append({"url": tool_dir + tool_name, "path": tool_dir + tool_name})
        remote_container = self._find_container(job_wrapper)
        remote_image = "galaxy/pulsar-pod-staging:0.14.0"

        if(hasattr(remote_container, "container_id")):
            remote_image = remote_container.container_id

        tool_script = os.path.join(job_wrapper.working_directory, "tool_script.sh")
        if os.path.exists(tool_script):
            client_inputs_list.append({"paths": tool_script})

        final_commands = ["/bin/bash", client_inputs_list[-1]["paths"]]

        referenced_tool_files = self.find_referenced_subfiles(tool_dir, job_wrapper.command_line, other_inputs)
        env_variables = job_wrapper.environment_variables
        execution_script = {
            "name": "Galaxy Job Execution",
            "description": job_wrapper.tool.description,
            "inputs": [],
            "outputs": [],
            "executors": [
                {
                    "image": remote_image,
                    "command": final_commands,
                }
            ]
        }

        for input in referenced_tool_files:
            execution_script["inputs"].append({"url": input, "path": input})

        for input in client_inputs_list:
            execution_script["inputs"].append({"url": input["paths"], "path": input["paths"]})

        for output in output_files:
            # execution_script["inputs"].append({"url": output, "path": output})
            execution_script["outputs"].append({"url": output, "path": output})

        for output in other_inputs:
            execution_script["inputs"].append({"url": output, "path": output})
            execution_script["outputs"].append({"url": output, "path": output})

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
        client_args, destination_params = self.get_upload_path(params, job_id)
        job_destination = job_wrapper.job_destination
        galaxy_id_tag = job_wrapper.get_id_tag()
        master_addr = job_destination.params.get("tes_master_addr")
        working_directory = job_wrapper.working_directory

        execution_script = self.__prepare_jobscript(job_wrapper)

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

    def _concat_job_log(self, data, key):
        s = ''
        # for i, log in enumerate(data['logs']):
        #     s += 'Step #{}\n'.format(i)
        #     s += log.get(key, '')
        return s

    def _concat_exit_codes(self, data):
        # TODO TES doesn't actually return the exit code yet
        return '0'
        # return ','.join([str(l['exitcode']) for l in data['logs']])

    def check_watched_item(self, job_state):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        job_id = job_state.job_id
        galaxy_id_tag = job_state.job_wrapper.get_id_tag()
        master_addr = job_state.job_wrapper.job_destination.params.get("tes_master_addr")

        data = self._get_job(master_addr, job_id)
        state = data['state']
        job_running = state == "RUNNING"
        job_complete = state == "COMPLETE"
        job_failed = "ERROR" or "CANCELED" in state

        # run_results = client.full_status()
        # remote_metadata_directory = run_results.get("metadata_directory", None)
        # stdout = run_results.get('stdout', '')
        # stderr = run_results.get('stderr', '')
        # exit_code = run_results.get('returncode', None)
        # job_metrics_directory = os.path.join(job_wrapper.working_directory, "metadata")
        # print '=' * 50
        # print state, job_state.running, data

        if job_running and job_state.running:
            return job_state

        if job_running and not job_state.running:
            log.debug("(%s/%s) job is now running" % (galaxy_id_tag, job_id))
            job_state.job_wrapper.change_state(model.Job.states.RUNNING)
            job_state.running = True
            return job_state

        # TODO this is from the condor backend. What's the right thing for TES?
        if not job_running and job_state.running:
            log.debug("(%s/%s) job has stopped running" % (galaxy_id_tag, job_id))
            # Will switching from RUNNING to QUEUED confuse Galaxy?
            # job_state.job_wrapper.change_state( model.Job.states.QUEUED )

        if job_complete:
            if job_state.job_wrapper.get_state() != model.Job.states.DELETED:
                # external_metadata = not asbool( job_state.job_wrapper.job_destination.params.get( "embed_metadata_in_job", True) )
                # if external_metadata:
                # self._handle_metadata_externally( job_state.job_wrapper, resolve_requirements=True )
                with open(job_state.output_file, 'w') as fh:
                    fh.write(self._concat_job_log(data, 'stdout'))

                with open(job_state.error_file, 'w') as fh:
                    fh.write(self._concat_job_log(data, 'stderr'))

                with open(job_state.exit_code_file, 'w') as fh:
                    fh.write(self._concat_exit_codes(data))

                log.debug("(%s/%s) job has completed" % (galaxy_id_tag, job_id))
                self.mark_as_finished(job_state)
            return

        if job_failed:
            log.debug("(%s/%s) job failed" % (galaxy_id_tag, job_id))
            self.mark_as_failed(job_state)
            return

        return job_state

    def stop_job(self, job_wrapper):
        """Attempts to delete a task from the task queue"""

        # Possibly the job was deleted before it was fully started.
        # In this case, the job_id will be None. This seems to be a bug in Galaxy.
        # It's likely that the job was in fact submitted to TES, but the job_id
        # wasn't persisted to the monitor queue?
        # TODO: This needs a thorough check why job Id is not coming with job_object
        # and why this is getting called after the job completion
        job = job_wrapper.get_job()

        job_id = job.job_runner_external_id
        if job_id is None:
            return

        master_addr = job.destination_params.get('tes_master_addr')
        self._cancel_job(master_addr, job_id)
        # TODO send cancel message to TES

    def recover(self, job, job_wrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        return
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

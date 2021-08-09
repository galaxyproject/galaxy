"""
Job control via TES.
"""
from lib.galaxy.jobs.runners.util.job_script import job_script
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

DEFAULT_GALAXY_URL = "http://localhost:8080/"


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
        self.galaxy_url = DEFAULT_GALAXY_URL
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

    def find_pattern_references(self, pattern, command_line, extra_files):
        """
        Finding the list of referenced file, using regex
        """
        referenced_files = set()
        for input_contents in self.__items(command_line, extra_files):
            referenced_files.update(findall(pattern, input_contents))
        return list(referenced_files)

    def file_creation_executor(self, mounted_dir, work_dir):
        """
        Returns the executor for creation of files
        """
        file_executor = {
            "workdir": mounted_dir,
            "image": "vipchhabra99/pulsar-lib",
            "command": ["/bin/bash",os.path.join(work_dir, 'createfiles.sh')]
            }
        return file_executor

    def job_executor(self, mounted_dir, remote_image, command_line, env):
        """
        Returns the executor for executing jobs
        """
        job_executor = {
            "workdir": mounted_dir,
            "image": remote_image,
            "command": command_line.split(),
            "env": env
            }
        return job_executor

    def file_staging_out_executor(self, mounted_dir, command):
        """
        Returns the executor for staging out of the files
        """
        staging_out_executor = {
            "workdir" : mounted_dir,
            "image" : "vipchhabra99/pulsar-lib",
            "command" : command
            }
        return staging_out_executor
    
    def base_job_script(self, mounted_dir, work_dir, output_files, description):
        """
        Retruns the basic structure for job-script
        """
        execution_script = {
            "name": "Galaxy Job Execution",
            "description": description,
            "inputs": [
                {
                    "path": os.path.join(work_dir, 'createfiles.sh'),
                    "content" : self.output_file_gen_script(output_files),
                    }],
            "executors": [],
            "volumes": [mounted_dir]
        }
        
        return execution_script

    def output_file_gen_script(self, output_files):
        """
            Generates shell script for generating output files in container
        """
        script = []
        
        for file in output_files:
            dir_name = os.path.split(file)[0]
            script.extend(['mkdir', '-p', dir_name, '&&',  'touch', file, '&&'])
        
        script[-1] = '\n'
        return ' '.join(script)

    def staging_out_command(self, script_path, output_files, api_url):
        """
            Generates command for staging out of files
        """
        command = ["python", script_path, api_url]

        for file in output_files:
            command.append(file)
        
        return command

    def env_variables(self, job_wrapper):
        """
            Get environment variables from job_wrapper
        """
        env_vars = {}
        for variable in job_wrapper.environment_variables:
            env_vars[variable['name']] = variable['value']
        env_vars["_GALAXY_JOB_TMP_DIR"] = self.container_workdir
        env_vars["_GALAXY_JOB_HOME_DIR"] = self.container_workdir
        return env_vars

    def input_url(self, api_url, path):
        """
            Get URL for path
        """
        file_link = f"{api_url}&path={path}"
        return file_link

    def input_descriptors(self, api_url, input_paths, type = "FILE"):
        """
            Get Input Descriptor for Jobfile
        """
        input_description = []

        for path in input_paths:
            input_description.append({
                "url" : self.input_url(api_url, path),
                "path" : path,
                "type" : type
            })
        return input_description

    def get_job_directory_files(self, work_dir):
        """
        Get path for all the files from work directory
        """
        paths = []
        for root, _ , files in os.walk(work_dir):
            for file in files:
                paths.append(os.path.join(root, file))
        
        return paths

    def build_script(self, job_wrapper, client_args):
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

        remote_container = self._find_container(job_wrapper)
        remote_image = "vipchhabra99/pulsar-lib"

        if(hasattr(remote_container, "container_id")):
            remote_image = remote_container.container_id

        command_line = build_command(
                self,
                job_wrapper=job_wrapper,
                include_metadata=False,
                create_tool_working_directory=False,
                include_work_dir_outputs=False,
                remote_job_directory=job_wrapper.working_directory,
            )

        env_var = self.env_variables(job_wrapper)
        staging_out_command = self.staging_out_command(script_path, output_files, client_args['files_endpoint'])
        
        job_script = self.base_job_script(mount_path, work_dir, output_files, job_wrapper.tool.description)
        
        job_script["inputs"].extend(self.input_descriptors(client_args['files_endpoint'], [script_path]))
        job_script["inputs"].extend(self.input_descriptors(client_args['files_endpoint'], tool_files))
        job_script["inputs"].extend(self.input_descriptors(client_args['files_endpoint'], self.get_job_directory_files(work_dir)))
        job_script["inputs"].extend(self.input_descriptors(client_args['files_endpoint'], input_files))

        job_script["executors"].append(self.file_creation_executor(mount_path, work_dir))
        job_script["executors"].append(self.job_executor(mount_path, remote_image, command_line, env_var))
        job_script["executors"].append(self.file_staging_out_executor(mount_path, staging_out_command))
        
        return job_script

    def __get_inputs(self, job_wrapper):
        """Returns the list about the details of input files."""

        input_files = []

        for input_dataset_wrapper in job_wrapper.get_input_paths():
            path = str(input_dataset_wrapper)
            input_files.append(path)

        return input_files

    def queue_job(self, job_wrapper):
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

        if(hasattr(job_wrapper.app, "galaxy_url")):
            self.galaxy_url = f"{job_wrapper.app.galaxy_url.rstrip('/')}/"

        if('galaxy_url' in job_destination.params):
            self.galaxy_url = job_destination.params.get("galaxy_url")

        job_script = self.build_script(job_wrapper, client_args)
        job_id = self._send_task(master_addr, job_script)

        job_state = TESJobState(
            job_id=job_id,
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper
        )

        log.info("(%s) queued as %s" % (galaxy_id_tag, job_id))
        job_wrapper.set_job_destination(job_destination, job_id)
        self.monitor_job(job_state)

    def get_output_files(self, job_wrapper):
        """
        Utility for getting list of Output Files
        """
        output_paths = job_wrapper.get_output_fnames()
        return [str(o) for o in output_paths]   # Force job_path from DatasetPath objects.

    def get_input_files(self, job_wrapper):
        """"
        Utility for getting list of Input Files
        """
        input_paths = job_wrapper.get_input_paths()
        return [str(i) for i in input_paths]

    def __finish_job(self, stdout, stderr, exit_code, job_wrapper):
        """
        Utility for finishing job after completion
        """
        
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
        """"
        Utility for concatination required job logs
        """
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
        """"
        Utility for getting out exit code of the job
        """
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
            stdout = self._concat_job_log(data, 'stdout')
            stderr = self._concat_job_log(data, 'stderr')
            exit_code = 1
            self.__finish_job(stdout, stderr, exit_code, job_state.job_wrapper)
            return

        return job_state

    def stop_job(self, job_wrapper):
        """Attempts to delete a task from the task queue"""
        #TODO: Need to check why this is getting called after the job completion in failed case
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
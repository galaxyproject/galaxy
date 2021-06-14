"""
Job control via TES.
"""
import logging
import os
import json
import shlex

import requests

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)
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
        # TODO TES doesn't actually shutdown running jobs.
        url = master_addr + "/v1/tasks" + str(job_id) + ":cancel"
        r = requests.post(url)

    def queue_job(self, job_wrapper):
        """Submit the job to TES."""

        log.debug(f"Starting queue_job for job {job_wrapper.get_id_tag()}")
        include_metadata = asbool(job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
        if not self.prepare_job(job_wrapper, include_metadata=include_metadata):
            return

        log.debug(f"Details of Job Wrapper object {job_wrapper.__dict__}")
        job_destination = job_wrapper.job_destination
        galaxy_id_tag = job_wrapper.get_id_tag()
        master_addr = job_destination.params.get("tes_master_addr")
        commands = job_wrapper.command_line
        commands = commands.split()
        working_directory = job_wrapper.working_directory
        # container = job_wrapper.tool.containers[0]

        # print '=' * 50
        # print job_wrapper.command_line
        # print
        script_path = commands[1][1:-1]
        # script_path = "/home/vipulchhabra/Desktop/GSoC/funnel-linux-amd64-0.10.0/fasta_to_tabular_converter.py"
        input_file = commands[2][9:-1]
        output_file = commands[3][10:-1]
        commands[1] = "/inputs/test.py"
        commands[2] = "--input=/inputs/input.dat"
        commands[3] = "--output=/outputs/output.dat"
        execution_script = {
            "name": "Task Executors",
            "description": job_wrapper.tool.description,
            "inputs": [
                {
                    "url": script_path,
                    "path": "/inputs/test.py"
                },
                {
                    "url": input_file,
                    "path": "/inputs/input.dat"
                }
            ],
            "outputs": [
                {
                    "url": output_file,
                    "path": "/outputs/output.dat"
                }
            ],
            "executors": [
                {
                    "image": "python",
                    "command": commands,
                }
            ]
        }

        job_id = self._send_task(master_addr, execution_script)

        job_state = TESJobState(
            job_id=job_id,
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper
        )

        log.info("(%s) queued as %s" % (galaxy_id_tag, job_id))
        job_wrapper.set_job_destination(job_destination, job_id)
        self.monitor_job(job_state)

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
        job_failed = "ERROR" in state

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

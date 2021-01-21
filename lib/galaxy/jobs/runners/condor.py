"""Job control via the Condor DRM via CLI.

This plugin has been used in production and isn't unstable but shouldn't be taken as an
example of how to write Galaxy job runners that interface with a DRM using command-line
invocations. When writing new job runners that leverage command-line calls for submitting
and checking the status of jobs please check out the CLI runner (cli.py in this directory)
start by writing a new job plugin in for that (see examples in
/galaxy/jobs/runners/util/cli/job). That approach will result in less boilerplate and allow
greater reuse of the DRM specific hooks you'll need to write. Ideally this plugin would
have been written to target that framework, but we don't have the bandwidth to rewrite
it at this time.
"""
import datetime
import logging
import os
import subprocess

import htcondor
from htcondor import JobEventType

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)
from galaxy.jobs.runners.util.condor import (
    build_submit_description,
    submission_params
)
from galaxy.util import asbool


log = logging.getLogger(__name__)

__all__ = ('CondorJobRunner', )


class CondorJobState(AsynchronousJobState):
    def __init__(self, **kwargs):
        """
        Encapsulates state related to a job that is being run via the DRM and
        that we need to monitor.
        """
        super().__init__(**kwargs)
        self.failed = False
        self.user_log = None
        self.last_seen_event = None
        self.job_event_log = None


class CondorJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "CondorRunner"

    def __init__(self, app, nworkers):
        """Initialize this job runner and start the monitor thread"""
        super().__init__(app, nworkers)
        self._init_monitor_thread()
        self._init_worker_threads()
        self.schedd = htcondor.Schedd()

    def queue_job(self, job_wrapper):
        """Create job script and submit it to the DRM"""

        # prepare the job
        include_metadata = asbool(job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
        if not self.prepare_job(job_wrapper, include_metadata=include_metadata):
            return

        # get configured job destination
        job_destination = job_wrapper.job_destination

        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()

        # get destination params
        query_params = submission_params(prefix="", **job_destination.params)
        container = None
        universe = query_params.get('universe', None)
        if universe and universe.strip().lower() == 'docker':
            container = self._find_container(job_wrapper)
            if container:
                # HTCondor needs the image as 'docker_image'
                query_params.update({'docker_image': container.container_id})

        galaxy_slots = query_params.get('request_cpus', None)
        if galaxy_slots:
            galaxy_slots_statement = 'GALAXY_SLOTS="%s"; export GALAXY_SLOTS_CONFIGURED="1"' % galaxy_slots
        else:
            galaxy_slots_statement = 'GALAXY_SLOTS="1"'

        # define job attributes
        cjs = CondorJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper
        )

        cjs.user_log = os.path.join(job_wrapper.working_directory, 'galaxy_%s.condor.log' % galaxy_id_tag)
        cjs.register_cleanup_file_attribute('user_log')
        executable = cjs.job_file

        submit_params = dict(
            executable=executable,
            output=cjs.output_file,
            error=cjs.error_file,
            log=cjs.user_log
        )

        submit_file_contents = build_submit_description(submit_params, query_params)
        htcondor_job = htcondor.Submit(submit_file_contents)

        script = self.get_job_file(
            job_wrapper,
            exit_code_path=cjs.exit_code_file,
            slots_statement=galaxy_slots_statement,
            shell=job_wrapper.shell,
        )
        try:
            self.write_executable_script(executable, script)
        except Exception:
            job_wrapper.fail("failure preparing job script", exception=True)
            log.exception("(%s) failure preparing job script" % galaxy_id_tag)
            return

        cleanup_job = job_wrapper.cleanup_job

        # job was deleted while we were preparing it
        if job_wrapper.get_state() in (model.Job.states.DELETED, model.Job.states.STOPPED):
            log.debug("(%s) Job deleted/stopped by user before it entered the queue", galaxy_id_tag)
            if cleanup_job in ("always", "onsuccess"):
                cjs.cleanup()
                job_wrapper.cleanup()
            return

        log.debug(f"({galaxy_id_tag}) submitting file {executable}")

        with self.schedd.transaction() as txn:
            external_job_id = htcondor_job.queue(txn)

        log.info(f"({galaxy_id_tag}) queued as {external_job_id}")

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_external_id(external_job_id)

        # Store DRM related state information for job
        cjs.job_id = external_job_id
        cjs.job_destination = job_destination
        cjs.job_event_log = htcondor.JobEventLog(cjs.user_log)

        # Add to our 'queue' of jobs to monitor
        self.monitor_queue.put(cjs)

    def check_watched_items(self):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []
        for cjs in self.watched:
            job_id = cjs.job_id
            galaxy_id_tag = cjs.job_wrapper.get_id_tag()

            try:
                CJS_EXECUTE = CJS_SHADOW_EXCEPTION = CJS_EVICTED = CJS_TERMINATED = CJS_ABORTED = False
                if not cjs.job_event_log:
                    cjs.job_event_log = htcondor.JobEventLog(cjs.user_log)

                for event in cjs.job_event_log.events(stop_after=0):
                    cjs.last_seen_event = datetime.datetime.fromtimestamp(event.timestamp)  # can be used to check for the job via polling
                    if event.type is JobEventType.EXECUTE:
                        CJS_EXECUTE = True
                    elif event.type is JobEventType.JOB_EVICTED:
                        CJS_EVICTED = True
                    elif event.type is JobEventType.SHADOW_EXCEPTION:
                        CJS_SHADOW_EXCEPTION = True
                    elif event.type is JobEventType.JOB_TERMINATED:
                        CJS_TERMINATED = True
                    elif event.type is JobEventType.JOB_ABORTED:
                        CJS_ABORTED = True

                """
                Condor JobStatus codes
                0	Unexpanded 	U
                1	Idle 	I
                2	Running 	R
                3	Removed 	X
                4	Completed 	C
                5	Held 	H
                6	Submission_err 	E
                """
                # If for one day nothing happend try polling the job to be sure we have not lost it
                # More information about event based job tracking and polling can be found here:
                # https://htcondor.readthedocs.io/en/latest/apis/python-bindings/tutorials/Scalable-Job-Tracking.html
                time_delta = datetime.datetime.now() - cjs.last_seen_event
                if time_delta.days > 1:
                    cjs.last_seen_event = datetime.datetime.now()
                    schedd_query = self.schedd.history(
                        constraint=f"ClusterId == {job_id}",
                        projection=["JobStatus"]
                    )
                    for res in schedd_query:
                        status = res.get('JobStatus')
                        job_running = False
                    if status == 4:
                        job_complete = True
                        job_failed = False
                    elif status in [3, 6]:
                        job_complete = False
                        job_failed = True

                if cjs.job_wrapper.tool.tool_type != 'interactive' and not any([CJS_EXECUTE, CJS_SHADOW_EXCEPTION, CJS_EVICTED, CJS_TERMINATED, CJS_ABORTED]):
                    new_watched.append(cjs)
                    continue

                job_running = CJS_EXECUTE and not (CJS_SHADOW_EXCEPTION or CJS_EVICTED)
                job_complete = CJS_TERMINATED
                job_failed = CJS_ABORTED

            except Exception:
                # so we don't kill the monitor thread
                log.exception(f"({galaxy_id_tag}/{job_id}) Unable to check job status")
                log.warning(f"({galaxy_id_tag}/{job_id}) job will now be errored")
                cjs.fail_message = "Cluster could not complete job"
                self.work_queue.put((self.fail_job, cjs))
                continue

            if job_running:
                # If running, check for entry points...
                cjs.job_wrapper.check_for_entry_points()

            if job_running and not cjs.running:
                log.debug(f"({galaxy_id_tag}/{job_id}) job is now running")
                cjs.job_wrapper.change_state(model.Job.states.RUNNING)
            if not job_running and cjs.running:
                log.debug(f"({galaxy_id_tag}/{job_id}) job has stopped running")
                # Will switching from RUNNING to QUEUED confuse Galaxy?
                # cjs.job_wrapper.change_state( model.Job.states.QUEUED )
            job_state = cjs.job_wrapper.get_state()
            if job_complete or job_state == model.Job.states.STOPPED:
                if job_state != model.Job.states.DELETED:
                    external_metadata = not asbool(cjs.job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
                    if external_metadata:
                        self._handle_metadata_externally(cjs.job_wrapper, resolve_requirements=True)
                    log.debug(f"({galaxy_id_tag}/{job_id}) job has completed")
                    self.work_queue.put((self.finish_job, cjs))
                continue
            if job_failed:
                log.debug(f"({galaxy_id_tag}/{job_id}) job failed")
                cjs.failed = True
                self.work_queue.put((self.finish_job, cjs))
                continue
            cjs.runnning = job_running
            new_watched.append(cjs)
        # Replace the watch list with the updated version
        self.watched = new_watched

    def stop_job(self, job_wrapper):
        """Attempts to delete a job from the DRM queue"""
        job = job_wrapper.get_job()
        external_id = job.job_runner_external_id
        galaxy_id_tag = job_wrapper.get_id_tag()
        if job.container:
            try:
                log.info(f"stop_job(): {job.id}: trying to stop container .... ({external_id})")
                # self.watched = [cjs for cjs in self.watched if cjs.job_id != external_id]
                new_watch_list = list()
                cjs = None
                for tcjs in self.watched:
                    if tcjs.job_id != external_id:
                        new_watch_list.append(tcjs)
                    else:
                        cjs = tcjs
                        break
                self.watched = new_watch_list
                self._stop_container(job_wrapper)
                # self.watched.append(cjs)
                if cjs.job_wrapper.get_state() != model.Job.states.DELETED:
                    external_metadata = not asbool(cjs.job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
                    if external_metadata:
                        self._handle_metadata_externally(cjs.job_wrapper, resolve_requirements=True)
                    log.debug(f"({galaxy_id_tag}/{external_id}) job has completed")
                    self.work_queue.put((self.finish_job, cjs))
            except Exception as e:
                log.warning(f"stop_job(): {job.id}: trying to stop container failed. ({e})")
                try:
                    self._kill_container(job_wrapper)
                except Exception as e:
                    log.warning(f"stop_job(): {job.id}: trying to kill container failed. ({e})")
                    self._condor_stop(external_id)
        else:
            self._condor_stop(external_id)

    def _condor_stop(self, external_id):
        self.schedd.act(htcondor.JobAction.Remove, f"ClusterId == {external_id}")

    def recover(self, job, job_wrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        # TODO Check if we need any changes here
        job_id = job.get_job_runner_external_id()
        galaxy_id_tag = job_wrapper.get_id_tag()
        if job_id is None:
            self.put(job_wrapper)
            return
        cjs = CondorJobState(job_wrapper=job_wrapper, files_dir=job_wrapper.working_directory)
        cjs.job_id = job_id
        cjs.command_line = job.get_command_line()
        cjs.job_wrapper = job_wrapper
        cjs.job_destination = job_wrapper.job_destination
        cjs.user_log = os.path.join(job_wrapper.working_directory, 'galaxy_%s.condor.log' % galaxy_id_tag)
        cjs.register_cleanup_file_attribute('user_log')
        if job.state in (model.Job.states.RUNNING, model.Job.states.STOPPED):
            log.debug(f"({job.id}/{job.get_job_runner_external_id()}) is still in {job.state} state, adding to the DRM queue")
            cjs.running = True
            self.monitor_queue.put(cjs)
        elif job.state == model.Job.states.QUEUED:
            log.debug(f"({job.id}/{job.job_runner_external_id}) is still in DRM queued state, adding to the DRM queue")
            cjs.running = False
            self.monitor_queue.put(cjs)

    def _stop_container(self, job_wrapper):
        return self._run_container_command(job_wrapper, 'stop')

    def _kill_container(self, job_wrapper):
        return self._run_container_command(job_wrapper, 'kill')

    def _run_container_command(self, job_wrapper, command):
        job = job_wrapper.get_job()
        external_id = job.job_runner_external_id
        if job:
            cont = job.container
            if cont:
                if cont.container_type == 'docker':
                    return self._run_command(cont.container_info['commands'][command], external_id)[0]

    def _run_command(self, command, external_job_id):
        command = f'condor_ssh_to_job {external_job_id} {command}'

        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, close_fds=True, preexec_fn=os.setpgrp)
        stdout, stderr = p.communicate()
        exit_code = p.returncode
        ret = None
        if exit_code == 0:
            ret = stdout.strip()
        else:
            log.debug(stderr)
        # exit_code = subprocess.call(command,
        #                            shell=True,
        #                            preexec_fn=os.setpgrp)
        log.debug('_run_command(%s) exit code (%s) and failure: %s', command, exit_code, stderr)
        return (exit_code, ret)

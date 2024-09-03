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

import logging
import os
import subprocess

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.jobs.runners.util.condor import (
    build_submit_description,
    condor_stop,
    condor_submit,
    submission_params,
    summarize_condor_log,
)
from galaxy.util import asbool

log = logging.getLogger(__name__)

__all__ = ("CondorJobRunner",)


class CondorJobState(AsynchronousJobState):
    def __init__(self, **kwargs):
        """
        Encapsulates state related to a job that is being run via the DRM and
        that we need to monitor.
        """
        super().__init__(**kwargs)
        self.failed = False
        self.user_log = None
        self.user_log_size = 0


class CondorJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """

    runner_name = "CondorRunner"

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
        universe = query_params.get("universe", None)
        if universe and universe.strip().lower() == "docker":
            container = self._find_container(job_wrapper)
            if container:
                # HTCondor needs the image as 'docker_image'
                query_params.update({"docker_image": container.container_id})

        if galaxy_slots := query_params.get("request_cpus", None):
            galaxy_slots_statement = f'GALAXY_SLOTS="{galaxy_slots}"; export GALAXY_SLOTS; GALAXY_SLOTS_CONFIGURED="1"; export GALAXY_SLOTS_CONFIGURED;'
        else:
            galaxy_slots_statement = 'GALAXY_SLOTS="1"; export GALAXY_SLOTS;'

        # define job attributes
        cjs = CondorJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper)

        cjs.user_log = os.path.join(job_wrapper.working_directory, f"galaxy_{galaxy_id_tag}.condor.log")
        cjs.register_cleanup_file_attribute("user_log")
        submit_file = os.path.join(job_wrapper.working_directory, f"galaxy_{galaxy_id_tag}.condor.desc")
        executable = cjs.job_file

        build_submit_params = dict(
            executable=executable,
            output=cjs.output_file,
            error=cjs.error_file,
            user_log=cjs.user_log,
            query_params=query_params,
        )

        submit_file_contents = build_submit_description(**build_submit_params)
        script = self.get_job_file(
            job_wrapper,
            exit_code_path=cjs.exit_code_file,
            slots_statement=galaxy_slots_statement,
            shell=job_wrapper.shell,
        )
        try:
            self.write_executable_script(executable, script, job_io=job_wrapper.job_io)
        except Exception:
            job_wrapper.fail("failure preparing job script", exception=True)
            log.exception(f"({galaxy_id_tag}) failure preparing job script")
            return

        cleanup_job = job_wrapper.cleanup_job
        try:
            open(submit_file, "w").write(submit_file_contents)
        except Exception:
            if cleanup_job == "always":
                cjs.cleanup()
                # job_wrapper.fail() calls job_wrapper.cleanup()
            job_wrapper.fail("failure preparing submit file", exception=True)
            log.exception(f"({galaxy_id_tag}) failure preparing submit file")
            return

        # job was deleted while we were preparing it
        if job_wrapper.get_state() in (model.Job.states.DELETED, model.Job.states.STOPPED):
            log.debug("(%s) Job deleted/stopped by user before it entered the queue", galaxy_id_tag)
            if cleanup_job in ("always", "onsuccess"):
                os.unlink(submit_file)
                cjs.cleanup()
                job_wrapper.cleanup()
            return

        log.debug(f"({galaxy_id_tag}) submitting file {executable}")

        external_job_id, message = condor_submit(submit_file)
        if external_job_id is None:
            log.debug(f"condor_submit failed for job {job_wrapper.get_id_tag()}: {message}")
            if self.app.config.cleanup_job == "always":
                os.unlink(submit_file)
                cjs.cleanup()
            job_wrapper.fail("condor_submit failed", exception=True)
            return

        os.unlink(submit_file)

        log.info(f"({galaxy_id_tag}) queued as {external_job_id}")

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_external_id(external_job_id)

        # Store DRM related state information for job
        cjs.job_id = external_job_id
        cjs.job_destination = job_destination

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
                if (
                    cjs.job_wrapper.tool.tool_type != "interactive"
                    and os.stat(cjs.user_log).st_size == cjs.user_log_size
                ):
                    new_watched.append(cjs)
                    continue
                s1, s4, s7, s5, s9, log_size = summarize_condor_log(cjs.user_log, job_id)
                job_running = s1 and not (s4 or s7)
                job_complete = s5
                job_failed = s9
                cjs.user_log_size = log_size
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
                    external_metadata = not asbool(
                        cjs.job_wrapper.job_destination.params.get("embed_metadata_in_job", True)
                    )
                    if external_metadata:
                        self._handle_metadata_externally(cjs.job_wrapper, resolve_requirements=True)
                    log.debug(f"({galaxy_id_tag}/{job_id}) job has completed")
                    self.work_queue.put((self.finish_job, cjs))
                continue
            if job_failed:
                log.debug(f"({galaxy_id_tag}/{job_id}) job failed")
                cjs.failed = True
                self.work_queue.put((self.fail_job, cjs))
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
                new_watch_list = []
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
                    external_metadata = not asbool(
                        cjs.job_wrapper.job_destination.params.get("embed_metadata_in_job", True)
                    )
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
                    failure_message = condor_stop(external_id)
                    if failure_message:
                        log.debug(f"({external_id}). Failed to stop condor {failure_message}")
        else:
            failure_message = condor_stop(external_id)
            if failure_message:
                log.debug(f"({external_id}). Failed to stop condor {failure_message}")

    def recover(self, job, job_wrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        # TODO Check if we need any changes here
        job_id = job.get_job_runner_external_id()
        galaxy_id_tag = job_wrapper.get_id_tag()
        if job_id is None:
            self.put(job_wrapper)
            return
        cjs = CondorJobState(job_wrapper=job_wrapper, files_dir=job_wrapper.working_directory)
        cjs.job_id = str(job_id)
        cjs.command_line = job.get_command_line()
        cjs.job_wrapper = job_wrapper
        cjs.job_destination = job_wrapper.job_destination
        cjs.user_log = os.path.join(job_wrapper.working_directory, f"galaxy_{galaxy_id_tag}.condor.log")
        cjs.register_cleanup_file_attribute("user_log")
        if job.state in (model.Job.states.RUNNING, model.Job.states.STOPPED):
            log.debug(
                f"({job.id}/{job.get_job_runner_external_id()}) is still in {job.state} state, adding to the DRM queue"
            )
            cjs.running = True
            self.monitor_queue.put(cjs)
        elif job.state == model.Job.states.QUEUED:
            log.debug(f"({job.id}/{job.job_runner_external_id}) is still in DRM queued state, adding to the DRM queue")
            cjs.running = False
            self.monitor_queue.put(cjs)

    def _stop_container(self, job_wrapper):
        return self._run_container_command(job_wrapper, "stop")

    def _kill_container(self, job_wrapper):
        return self._run_container_command(job_wrapper, "kill")

    def _run_container_command(self, job_wrapper, command):
        job = job_wrapper.get_job()
        external_id = job.job_runner_external_id
        if job:
            cont = job.container
            if cont:
                if cont.container_type == "docker":
                    return self._run_command(cont.container_info["commands"][command], external_id)[0]

    def _run_command(self, command, external_job_id):
        command = f"condor_ssh_to_job {external_job_id} {command}"

        p = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, close_fds=True, preexec_fn=os.setpgrp
        )
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
        log.debug("_run_command(%s) exit code (%s) and failure: %s", command, exit_code, stderr)
        return (exit_code, ret)

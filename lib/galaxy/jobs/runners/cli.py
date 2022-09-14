"""
Job control via a command line interface (e.g. qsub/qstat), possibly over a remote connection (e.g. ssh).
"""

import logging
import time

from galaxy import model
from galaxy.jobs import JobDestination
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
    JobState,
)
from galaxy.util import asbool
from .util.cli import (
    CliInterface,
    split_params,
)

log = logging.getLogger(__name__)

__all__ = ("ShellJobRunner",)

DEFAULT_EMBED_METADATA_IN_JOB = True
MAX_SUBMIT_RETRY = 3


class ShellJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """

    runner_name = "ShellRunner"

    def __init__(self, app, nworkers):
        """Start the job runner"""
        super().__init__(app, nworkers)

        self.cli_interface = CliInterface()

    def get_cli_plugins(self, shell_params, job_params):
        return self.cli_interface.get_plugins(shell_params, job_params)

    def url_to_destination(self, url):
        params = {}
        shell_params, job_params = url.split("/")[2:4]
        # split 'foo=bar&baz=quux' into { 'foo' : 'bar', 'baz' : 'quux' }
        shell_params = {f"shell_{k}": v for k, v in [kv.split("=", 1) for kv in shell_params.split("&")]}
        job_params = {f"job_{k}": v for k, v in [kv.split("=", 1) for kv in job_params.split("&")]}
        params.update(shell_params)
        params.update(job_params)
        log.debug(f"Converted URL '{url}' to destination runner=cli, params={params}")
        # Create a dynamic JobDestination
        return JobDestination(runner="cli", params=params)

    def parse_destination_params(self, params):
        return split_params(params)

    def queue_job(self, job_wrapper):
        """Create job script and submit it to the DRM"""
        # prepare the job
        include_metadata = asbool(
            job_wrapper.job_destination.params.get("embed_metadata_in_job", DEFAULT_EMBED_METADATA_IN_JOB)
        )
        if not self.prepare_job(job_wrapper, include_metadata=include_metadata):
            return

        # Get shell and job execution interface
        job_destination = job_wrapper.job_destination
        shell_params, job_params = self.parse_destination_params(job_destination.params)
        shell, job_interface = self.get_cli_plugins(shell_params, job_params)

        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()

        # define job attributes
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper)

        job_file_kwargs = job_interface.job_script_kwargs(ajs.output_file, ajs.error_file, ajs.job_name)
        script = self.get_job_file(
            job_wrapper, exit_code_path=ajs.exit_code_file, shell=job_wrapper.shell, **job_file_kwargs
        )

        try:
            self.write_executable_script(ajs.job_file, script, job_io=job_wrapper.job_io)
        except Exception:
            log.exception(f"({galaxy_id_tag}) failure writing job script")
            job_wrapper.fail("failure preparing job script", exception=True)
            return

        # job was deleted while we were preparing it
        if job_wrapper.get_state() in (model.Job.states.DELETED, model.Job.states.STOPPED):
            log.debug("(%s) Job deleted/stopped by user before it entered the queue", galaxy_id_tag)
            if job_wrapper.cleanup_job in ("always", "onsuccess"):
                job_wrapper.cleanup()
            return

        log.debug(f"({galaxy_id_tag}) submitting file: {ajs.job_file}")

        returncode, stdout = self.submit(shell, job_interface, ajs.job_file, galaxy_id_tag, retry=MAX_SUBMIT_RETRY)
        if returncode != 0:
            job_wrapper.fail("failure submitting job")
            return
        # Some job runners return something like 'Submitted batch job XXXX'
        # Strip and split to get job ID.
        submit_stdout = stdout.strip()
        external_job_id = submit_stdout and submit_stdout.split()[-1]
        if not external_job_id:
            log.error(f"({galaxy_id_tag}) submission did not return a job identifier, failing job")
            job_wrapper.fail("failure submitting job")
            return

        log.info(f"({galaxy_id_tag}) queued with identifier: {external_job_id}")

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_external_id(external_job_id)

        # Store state information for job
        ajs.job_id = external_job_id
        ajs.old_state = "new"
        ajs.job_destination = job_destination

        # Add to our 'queue' of jobs to monitor
        self.monitor_queue.put(ajs)

    def submit(self, shell, job_interface, job_file, galaxy_id_tag, retry=MAX_SUBMIT_RETRY, timeout=10):
        """
        Handles actual job script submission.

        If submission fails will retry `retry` time with a timeout of `timeout` seconds.
        Retuns the returncode of the submission and the stdout, which contains the external job_id.
        """
        cmd_out = shell.execute(job_interface.submit(job_file))
        returncode = cmd_out.returncode
        if returncode == 0:
            stdout = cmd_out.stdout
            if not stdout or not stdout.strip():
                log.warning(
                    f"({galaxy_id_tag}) Execute returned a 0 exit code but no external identifier will be recovered from empty stdout - stderr is {cmd_out.stderr}"
                )
            return returncode, stdout
        stdout = f"({galaxy_id_tag}) submission failed (stdout): {cmd_out.stdout}"
        stderr = f"({galaxy_id_tag}) submission failed (stderr): {cmd_out.stderr}"
        if retry > 0:
            log.info("%s, retrying in %s seconds", stdout, timeout)
            log.info("%s, retrying in %s seconds", stderr, timeout)
            time.sleep(timeout)
            return self.submit(shell, job_interface, job_file, galaxy_id_tag, retry=retry - 1, timeout=timeout)
        else:
            log.error(stdout)
            log.error(stderr)
            return returncode, cmd_out.stdout

    def check_watched_items(self):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []

        job_states = self.__get_job_states()

        for ajs in self.watched:
            external_job_id = ajs.job_id
            id_tag = ajs.job_wrapper.get_id_tag()
            old_state = ajs.old_state
            state = job_states.get(external_job_id, None)
            if state is None:
                if ajs.job_wrapper.get_state() == model.Job.states.DELETED:
                    continue

                log.debug(f"({id_tag}/{external_job_id}) job not found in batch state check")
                shell_params, job_params = self.parse_destination_params(ajs.job_destination.params)
                shell, job_interface = self.get_cli_plugins(shell_params, job_params)
                cmd_out = shell.execute(job_interface.get_single_status(external_job_id))
                state = job_interface.parse_single_status(cmd_out.stdout, external_job_id)
                if not state == model.Job.states.OK:
                    log.warning(
                        f"({id_tag}/{external_job_id}) job not found in batch state check, but found in individual state check"
                    )
            job_state = ajs.job_wrapper.get_state()
            if state != old_state:
                log.debug(f"({id_tag}/{external_job_id}) state change: from {old_state} to {state}")
                if state == model.Job.states.ERROR and job_state != model.Job.states.STOPPED:
                    # Try to find out the reason for exiting - this needs to happen before change_state
                    # otherwise jobs depending on resubmission outputs see that job as failed and pause.
                    self.__handle_out_of_memory(ajs, external_job_id)
                    self.work_queue.put((self.mark_as_failed, ajs))
                    # Don't add the job to the watched items once it fails, deals with https://github.com/galaxyproject/galaxy/issues/7820
                    continue
                if not state == model.Job.states.OK:
                    # No need to change_state when the state is OK, this will be handled by `self.finish_job`
                    ajs.job_wrapper.change_state(state)
            if state == model.Job.states.RUNNING and not ajs.running:
                ajs.running = True
            ajs.old_state = state
            if state == model.Job.states.OK or job_state == model.Job.states.STOPPED:
                external_metadata = not asbool(
                    ajs.job_wrapper.job_destination.params.get("embed_metadata_in_job", DEFAULT_EMBED_METADATA_IN_JOB)
                )
                if external_metadata:
                    self.work_queue.put((self.handle_metadata_externally, ajs))
                log.debug(f"({id_tag}/{external_job_id}) job execution finished, running job wrapper finish method")
                self.work_queue.put((self.finish_job, ajs))
            else:
                new_watched.append(ajs)
        # Replace the watch list with the updated version
        self.watched = new_watched

    def handle_metadata_externally(self, ajs):
        self._handle_metadata_externally(ajs.job_wrapper, resolve_requirements=True)

    def __handle_out_of_memory(self, ajs, external_job_id):
        shell_params, job_params = self.parse_destination_params(ajs.job_destination.params)
        shell, job_interface = self.get_cli_plugins(shell_params, job_params)
        cmd_out = shell.execute(job_interface.get_failure_reason(external_job_id))
        if cmd_out is not None:
            if (
                job_interface.parse_failure_reason(cmd_out.stdout, external_job_id)
                == JobState.runner_states.MEMORY_LIMIT_REACHED
            ):
                ajs.runner_state = JobState.runner_states.MEMORY_LIMIT_REACHED
                ajs.fail_message = "Tool failed due to insufficient memory. Try with more memory."

    def __get_job_states(self):
        job_destinations = {}
        job_states = {}
        # unique the list of destinations
        for ajs in self.watched:
            if ajs.job_destination.id not in job_destinations:
                job_destinations[ajs.job_destination.id] = dict(
                    job_destination=ajs.job_destination, job_ids=[ajs.job_id]
                )
            else:
                job_destinations[ajs.job_destination.id]["job_ids"].append(ajs.job_id)
        # check each destination for the listed job ids
        for v in job_destinations.values():
            job_destination = v["job_destination"]
            job_ids = v["job_ids"]
            shell_params, job_params = self.parse_destination_params(job_destination.params)
            shell, job_interface = self.get_cli_plugins(shell_params, job_params)
            cmd_out = shell.execute(job_interface.get_status(job_ids))
            assert cmd_out.returncode == 0, cmd_out.stderr
            job_states.update(job_interface.parse_status(cmd_out.stdout, job_ids))
        return job_states

    def stop_job(self, job_wrapper):
        """Attempts to delete a dispatched job"""
        job = job_wrapper.get_job()
        try:
            shell_params, job_params = self.parse_destination_params(job.destination_params)
            shell, job_interface = self.get_cli_plugins(shell_params, job_params)
            cmd_out = shell.execute(job_interface.delete(job.job_runner_external_id))
            assert cmd_out.returncode == 0, cmd_out.stderr
            log.debug(f"({job.id}/{job.job_runner_external_id}) Terminated at user's request")
        except Exception as e:
            log.debug(
                f"({job.id}/{job.job_runner_external_id}) User killed running job, but error encountered during termination: {e}"
            )

    def recover(self, job, job_wrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_id = job.get_job_runner_external_id()
        if job_id is None:
            self.put(job_wrapper)
            return
        ajs = AsynchronousJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper,
            job_id=job_id,
            job_destination=job_wrapper.job_destination,
        )
        ajs.command_line = job.command_line
        if job.state in (model.Job.states.RUNNING, model.Job.states.STOPPED):
            log.debug(
                f"({job.id}/{job.job_runner_external_id}) is still in {job.state} state, adding to the runner monitor queue"
            )
            ajs.old_state = model.Job.states.RUNNING
            ajs.running = True
            self.monitor_queue.put(ajs)
        elif job.state == model.Job.states.QUEUED:
            log.debug(
                f"({job.id}/{job.job_runner_external_id}) is still in queued state, adding to the runner monitor queue"
            )
            ajs.old_state = model.Job.states.QUEUED
            ajs.running = False
            self.monitor_queue.put(ajs)

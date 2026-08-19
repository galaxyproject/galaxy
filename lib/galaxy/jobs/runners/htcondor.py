"""Job control via the HTCondor DRM using the htcondor2 Python API.

The HTCondor mechanics — the htcondor2 import, schedd clients, event-log
parsing and hold/failure classification — live in
:mod:`galaxy.jobs.runners.util.condor.htcondor`, which is shared with Pulsar.
This module maps that vocabulary onto Galaxy's job model.

See the Galaxy cluster documentation (doc/source/admin/cluster.md) for
configuration, architecture details, and testing instructions.
"""

import logging
import os
import shlex
import subprocess
from typing import TYPE_CHECKING

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.jobs.runners.util import runner_states
from galaxy.jobs.runners.util.condor import (
    build_submit_description,
    htcondor_helper,
    submission_params,
)
from galaxy.jobs.runners.util.condor.htcondor import (
    classify_failure_event,
    classify_hold,
    DEFAULT_MAX_HELD_COUNT,
    FAILURE_EXECUTABLE_ERROR,
    FAILURE_MESSAGES,
    held_message,
    HOLD_MESSAGES,
    HOLD_REASON_MEMORY_LIMIT,
    HOLD_REASON_WALLTIME,
    HTCondorClientCache,
    HTCondorEventLogTracker,
    import_htcondor,
    MISSING_LOG_GRACE_SECONDS,
    MISSING_LOG_MESSAGE,
    normalize_condor_config,
    parse_memory_mb,
    parse_walltime_seconds,
    periodic_hold_expression,
    SIGKILL,
    SIGKILL_MESSAGE,
    STATUS_ERROR_GRACE_SECONDS,
)
from galaxy.util import asbool

if TYPE_CHECKING:
    from galaxy.jobs import MinimalJobWrapper
    from galaxy.jobs.job_destination import JobDestination

log = logging.getLogger(__name__)

__all__ = ("HTCondorJobRunner",)

HTCONDOR_DESTINATION_KEYS = (
    "htcondor_collector",
    "htcondor_schedd",
    "htcondor_config",
    "request_walltime",
    "max_held_count",
    "embed_metadata_in_job",
)
HTCONDOR_REMOVE_REASON = "Galaxy job stop request"
# Module attribute rather than a re-export of the shared default so that tests
# can redirect the helper subprocess at a stub module.
HTCONDOR_HELPER_MODULE = htcondor_helper.__name__


class HTCondorJobState(AsynchronousJobState, HTCondorEventLogTracker):
    def __init__(
        self,
        job_wrapper: "MinimalJobWrapper",
        job_destination: "JobDestination",
        user_log: str,
        *,
        files_dir=None,
        job_id: str | None = None,
        job_file=None,
        output_file=None,
        error_file=None,
        exit_code_file=None,
        job_name=None,
    ) -> None:
        AsynchronousJobState.__init__(
            self,
            job_wrapper,
            job_destination,
            files_dir=files_dir,
            job_id=job_id,
            job_file=job_file,
            output_file=output_file,
            error_file=error_file,
            exit_code_file=exit_code_file,
            job_name=job_name,
        )
        HTCondorEventLogTracker.__init__(self, user_log)
        self.failed = False


class HTCondorJobRunner(AsynchronousJobRunner[HTCondorJobState]):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling.
    """

    runner_name = "HTCondorRunner"

    def __init__(self, app, nworkers, **kwargs):
        runner_param_specs = dict(
            htcondor_collector=dict(map=str, default=None),
            htcondor_schedd=dict(map=str, default=None),
            htcondor_config=dict(map=str, default=None),
        )
        if "runner_param_specs" not in kwargs:
            kwargs["runner_param_specs"] = {}
        kwargs["runner_param_specs"].update(runner_param_specs)

        super().__init__(app, nworkers, **kwargs)
        self.htcondor = import_htcondor()
        self._clients = HTCondorClientCache(
            self.htcondor,
            helper_module=HTCONDOR_HELPER_MODULE,
            remove_reason=HTCONDOR_REMOVE_REASON,
        )

    def shutdown(self):
        try:
            super().shutdown()
        finally:
            self._shutdown_clients()

    def _shutdown_clients(self) -> None:
        self._clients.shutdown()

    def _htcondor_params(self, job_destination: "JobDestination | None"):
        """Resolve collector/schedd/config parameters from the destination or runner defaults."""
        params = job_destination.params if job_destination is not None else {}
        collector = params.get("htcondor_collector", None) or self.runner_params.htcondor_collector
        schedd_name = params.get("htcondor_schedd", None) or self.runner_params.htcondor_schedd
        condor_config = params.get("htcondor_config", None) or self.runner_params.htcondor_config
        return collector, schedd_name, normalize_condor_config(condor_config)

    def _client_for_destination(self, job_destination: "JobDestination | None"):
        _, _, condor_config = self._htcondor_params(job_destination)
        return self._clients.client_for_config(condor_config)

    def _submit_params(self, job_destination: "JobDestination"):
        """Map destination params to submit params, excluding htcondor_* keys."""
        params = {k: v for k, v in job_destination.params.items() if k not in HTCONDOR_DESTINATION_KEYS}
        return submission_params(prefix="", **params)

    def queue_job(self, job_wrapper: "MinimalJobWrapper") -> None:
        """Create job script and submit it to the DRM."""

        include_metadata = asbool(job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
        if not self.prepare_job(job_wrapper, include_metadata=include_metadata):
            return

        job_destination = job_wrapper.job_destination
        galaxy_id_tag = job_wrapper.get_id_tag()
        collector, schedd_name, _ = self._htcondor_params(job_destination)

        query_params = self._submit_params(job_destination)
        # Set initialdir so HTCondor changes to the job working directory before
        # executing the script.
        query_params["initialdir"] = job_wrapper.working_directory
        container = None
        universe = query_params.get("universe", None)
        if universe and universe.strip().lower() == "docker":
            container = self._find_container(job_wrapper)
            if container:
                query_params.update({"docker_image": container.container_id})

        if galaxy_slots := query_params.get("request_cpus", None):
            galaxy_slots_statement = (
                f'GALAXY_SLOTS="{galaxy_slots}"; export GALAXY_SLOTS; '
                'GALAXY_SLOTS_CONFIGURED="1"; export GALAXY_SLOTS_CONFIGURED;'
            )
        else:
            galaxy_slots_statement = 'GALAXY_SLOTS="1"; export GALAXY_SLOTS;'

        galaxy_memory_statement = ""
        if request_memory := query_params.get("request_memory", None):
            memory_mb = parse_memory_mb(str(request_memory))
            if memory_mb is not None:
                slots = int(query_params.get("request_cpus", 1) or 1)
                per_slot = memory_mb // max(1, slots)
                galaxy_memory_statement = (
                    f'GALAXY_MEMORY_MB="{memory_mb}"; export GALAXY_MEMORY_MB; '
                    f'GALAXY_MEMORY_MB_PER_SLOT="{per_slot}"; export GALAXY_MEMORY_MB_PER_SLOT;'
                )

        if request_walltime := job_destination.params.get("request_walltime", None):
            walltime_seconds = parse_walltime_seconds(str(request_walltime))
            if walltime_seconds is not None and "periodic_hold" not in query_params:
                query_params["periodic_hold"] = periodic_hold_expression(walltime_seconds)

        cjs = HTCondorJobState(
            job_wrapper=job_wrapper,
            job_destination=job_destination,
            user_log=os.path.join(job_wrapper.working_directory, f"galaxy_{galaxy_id_tag}.condor.log"),
            files_dir=job_wrapper.working_directory,
        )
        cjs.register_cleanup_file_attribute("user_log")
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
            memory_statement=galaxy_memory_statement,
            shell=job_wrapper.shell,
        )
        try:
            self.write_executable_script(executable, script, job_io=job_wrapper.job_io)
        except Exception:
            job_wrapper.fail("failure preparing job script", exception=True)
            log.exception(f"({galaxy_id_tag}) failure preparing job script")
            return

        cleanup_job = job_wrapper.cleanup_job
        if job_wrapper.get_state() in (
            model.Job.states.DELETED,
            model.Job.states.STOPPED,
        ):
            log.debug(
                "(%s) Job deleted/stopped by user before it entered the queue",
                galaxy_id_tag,
            )
            if cleanup_job in ("always", "onsuccess"):
                cjs.cleanup()
                job_wrapper.cleanup()
            return

        log.debug(f"({galaxy_id_tag}) submitting file {executable}")

        try:
            external_job_id = self._client_for_destination(job_destination).submit(
                submit_file_contents,
                collector=collector,
                schedd_name=schedd_name,
            )
        except Exception:
            log.exception("htcondor submit failed for job %s", job_wrapper.get_id_tag())
            if cleanup_job == "always":
                cjs.cleanup()
            job_wrapper.fail("htcondor submit failed", exception=True)
            return

        log.info(f"({galaxy_id_tag}) queued as {external_job_id}")

        job_wrapper.set_external_id(external_job_id)
        cjs.job_id = external_job_id
        self.monitor_queue.put(cjs)

    def check_watched_items(self) -> None:
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []
        for cjs in self.watched:
            job_id = cjs.job_id
            galaxy_id_tag = cjs.job_wrapper.get_id_tag()
            if job_id is None:
                new_watched.append(cjs)
                continue
            try:
                summary = self._summarize_event_log(cjs)
                cjs.clear_status_errors()
            except Exception:
                elapsed = cjs.note_status_error()
                if elapsed < STATUS_ERROR_GRACE_SECONDS:
                    log.warning(
                        f"({galaxy_id_tag}/{job_id}) Transient error checking job status, "
                        f"will retry until it has persisted for {STATUS_ERROR_GRACE_SECONDS}s"
                    )
                    new_watched.append(cjs)
                    continue
                log.exception(f"({galaxy_id_tag}/{job_id}) Unable to check job status for {elapsed:.0f}s")
                log.warning(f"({galaxy_id_tag}/{job_id}) job will now be errored")
                cjs.fail_message = "Cluster could not complete job"
                cjs.runner_state = runner_states.UNKNOWN_ERROR
                cjs.close_event_log()
                self.work_queue.put((self.fail_job, cjs))
                continue

            job_running = summary.job_running
            job_complete = summary.job_complete
            failure_event = summary.failure_event
            job_held = summary.job_held
            term_signal = summary.term_signal
            hold_reason_code = summary.hold_reason_code

            if summary.log_missing:
                job_state = cjs.job_wrapper.get_state()
                if job_state in (
                    model.Job.states.DELETED,
                    model.Job.states.DELETING,
                    model.Job.states.STOPPED,
                    model.Job.states.STOPPING,
                ):
                    log.debug(f"({galaxy_id_tag}/{job_id}) job {job_state} while log was missing, stopping watch")
                    continue
                elapsed = cjs.note_missing_log()
                if elapsed >= MISSING_LOG_GRACE_SECONDS:
                    log.warning(f"({galaxy_id_tag}/{job_id}) event log absent for {elapsed:.0f}s, failing job")
                    cjs.fail_message = MISSING_LOG_MESSAGE
                    cjs.runner_state = runner_states.UNKNOWN_ERROR
                    cjs.close_event_log()
                    self.work_queue.put((self.fail_job, cjs))
                    continue
                log.debug(
                    f"({galaxy_id_tag}/{job_id}) event log not yet available "
                    f"(absent for {elapsed:.0f}s of {MISSING_LOG_GRACE_SECONDS}s)"
                )
                new_watched.append(cjs)
                continue
            cjs.clear_missing_log()

            if summary.job_released and cjs.held_count > 0:
                log.debug(f"({galaxy_id_tag}/{job_id}) job released, resetting held_count from {cjs.held_count} to 0")
                cjs.held_count = 0

            if job_running:
                cjs.job_wrapper.check_for_entry_points()

            if job_running and not cjs.running:
                log.debug(f"({galaxy_id_tag}/{job_id}) job is now running")
                cjs.job_wrapper.change_state(model.Job.states.RUNNING)
            if not job_running and cjs.running:
                log.debug(f"({galaxy_id_tag}/{job_id}) job has stopped running")

            job_state = cjs.job_wrapper.get_state()
            if job_complete or job_state == model.Job.states.STOPPED:
                if job_state != model.Job.states.DELETED:
                    # A SIGKILL on a non-user-stopped job is most likely an OOM kill.
                    if term_signal == SIGKILL and job_state != model.Job.states.STOPPED:
                        log.info(f"({galaxy_id_tag}/{job_id}) job killed by signal 9, likely OOM")
                        cjs.fail_message = SIGKILL_MESSAGE
                        cjs.runner_state = runner_states.MEMORY_LIMIT_REACHED
                        cjs.close_event_log()
                        self.work_queue.put((self.fail_job, cjs))
                        continue
                    external_metadata = not asbool(
                        cjs.job_wrapper.job_destination.params.get("embed_metadata_in_job", True)
                    )
                    if external_metadata:
                        self._handle_metadata_externally(cjs.job_wrapper, resolve_requirements=True)
                    log.debug(f"({galaxy_id_tag}/{job_id}) job has completed")
                    cjs.close_event_log()
                    self.work_queue.put((self.finish_job, cjs))
                continue
            if failure_event is not None:
                if job_state == model.Job.states.DELETED:
                    continue
                log.debug(f"({galaxy_id_tag}/{job_id}) job failed")
                cjs.failed = True
                self._apply_failure_event(cjs, failure_event)
                cjs.close_event_log()
                self.work_queue.put((self.fail_job, cjs))
                continue
            if job_held:
                if job_state not in (
                    model.Job.states.DELETED,
                    model.Job.states.STOPPED,
                ):
                    # Classify the hold by HoldReasonCode before applying the
                    # generic held_count escalation logic.
                    hold_reason = classify_hold(hold_reason_code)
                    if hold_reason == HOLD_REASON_MEMORY_LIMIT:
                        log.info(
                            f"({galaxy_id_tag}/{job_id}) job held for memory limit (HoldReasonCode={hold_reason_code})"
                        )
                        cjs.fail_message = HOLD_MESSAGES[hold_reason]
                        cjs.runner_state = runner_states.MEMORY_LIMIT_REACHED
                        cjs.close_event_log()
                        self.work_queue.put((self.fail_job, cjs))
                        continue
                    if hold_reason == HOLD_REASON_WALLTIME:
                        log.info(f"({galaxy_id_tag}/{job_id}) job held by periodic_hold expression (walltime)")
                        cjs.fail_message = HOLD_MESSAGES[hold_reason]
                        cjs.runner_state = runner_states.WALLTIME_REACHED
                        cjs.close_event_log()
                        self.work_queue.put((self.fail_job, cjs))
                        continue
                    cjs.held_count += 1
                    # max_held_count: destination parameter, counts distinct JOB_HELD events (default 3, 0 = disabled)
                    max_held_count = int(
                        cjs.job_wrapper.job_destination.params.get("max_held_count", DEFAULT_MAX_HELD_COUNT)
                    )
                    if max_held_count > 0 and cjs.held_count >= max_held_count:
                        log.warning(
                            f"({galaxy_id_tag}/{job_id}) Job held {cjs.held_count} "
                            "times without release, failing permanently"
                        )
                        cjs.fail_message = held_message(cjs.held_count)
                        cjs.runner_state = runner_states.UNKNOWN_ERROR
                        cjs.close_event_log()
                        self.work_queue.put((self.fail_job, cjs))
                        continue
                    cjs.job_wrapper.change_state(model.Job.states.QUEUED)
                cjs.running = False
                new_watched.append(cjs)
                continue
            cjs.running = job_running
            new_watched.append(cjs)
        self.watched = new_watched

    def stop_job(self, job_wrapper):
        """Attempts to delete a job from the DRM queue."""
        job = job_wrapper.get_job()
        external_id = job.job_runner_external_id
        if job.container:
            try:
                log.info(f"stop_job(): {job.id}: trying to stop container .... ({external_id})")
                self._stop_container(job_wrapper)
            except Exception as e:
                log.warning(f"stop_job(): {job.id}: trying to stop container failed. ({e})")
                try:
                    self._kill_container(job_wrapper)
                except Exception as e:
                    log.warning(f"stop_job(): {job.id}: trying to kill container failed. ({e})")
        failure_message = self._condor_remove(external_id, job_wrapper.job_destination)
        if failure_message:
            log.debug(f"({external_id}). Failed to stop condor {failure_message}")

    def recover(self, job: model.Job, job_wrapper: "MinimalJobWrapper") -> None:
        """Recovers jobs stuck in the queued/running state when Galaxy started."""
        job_id = job.get_job_runner_external_id()
        galaxy_id_tag = job_wrapper.get_id_tag()
        if job_id is None:
            self.put(job_wrapper)
            return
        cjs = HTCondorJobState(
            job_wrapper=job_wrapper,
            job_destination=job_wrapper.job_destination,
            user_log=os.path.join(job_wrapper.working_directory, f"galaxy_{galaxy_id_tag}.condor.log"),
            files_dir=job_wrapper.working_directory,
            job_id=str(job_id),
        )
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

    def _summarize_event_log(self, cjs: HTCondorJobState):
        if cjs.job_id is None:
            raise RuntimeError("Missing HTCondor job_id while summarizing event log.")
        return cjs.summarize(self.htcondor, int(cjs.job_id), cjs.running)

    def _apply_failure_event(self, cjs: HTCondorJobState, failure_event: int) -> None:
        """Set fail_message and runner_state on cjs based on the HTCondor failure event type."""
        failure = classify_failure_event(self.htcondor, failure_event)
        cjs.fail_message = FAILURE_MESSAGES[failure]
        if failure != FAILURE_EXECUTABLE_ERROR:
            # Executable errors are configuration problems, not transient.  runner_state is
            # intentionally left unset (None) so the resubmission framework never fires for
            # this case — only UNKNOWN_ERROR triggers resubmission handlers.
            cjs.runner_state = runner_states.UNKNOWN_ERROR

    def _condor_remove(self, external_id, job_destination: "JobDestination | None" = None):
        if not external_id:
            return "Missing external job id"
        try:
            job_spec: int | str = int(external_id)
        except Exception:
            job_spec = external_id
        try:
            collector, schedd_name, _ = self._htcondor_params(job_destination)
            self._client_for_destination(job_destination).remove(
                job_spec,
                collector=collector,
                schedd_name=schedd_name,
            )
        except Exception as e:
            return str(e)
        return None

    def _stop_container(self, job_wrapper):
        return self._run_container_command(job_wrapper, "stop")

    def _kill_container(self, job_wrapper):
        return self._run_container_command(job_wrapper, "kill")

    def _run_container_command(self, job_wrapper, command):
        job = job_wrapper.get_job()
        external_id = job.job_runner_external_id
        cont = job.container
        if cont and cont.container_type == "docker":
            return self._run_command(cont.container_info["commands"][command], external_id)

    def _run_command(self, command, external_job_id):
        cmd = ["condor_ssh_to_job", str(external_job_id)] + shlex.split(command)
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            close_fds=True,
            preexec_fn=os.setpgrp,
        )
        stdout, stderr = p.communicate()
        exit_code = p.returncode
        if exit_code != 0:
            log.debug(stderr)
        log.debug("_run_command(%s) exit code (%s) and failure: %s", cmd, exit_code, stderr)
        return exit_code

"""Job control via the HTCondor DRM using the htcondor2 Python API."""

import logging
import os
import subprocess
import threading
from typing import (
    TYPE_CHECKING,
    Optional,
    Union,
)

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.jobs.runners.util.condor import (
    build_submit_description,
    submission_params,
)
from galaxy.util import asbool

if TYPE_CHECKING:
    from galaxy.jobs import MinimalJobWrapper
    from galaxy.jobs.job_destination import JobDestination

log = logging.getLogger(__name__)

__all__ = ("HTCondorJobRunner",)

HTCONDOR_DESTINATION_KEYS = ("htcondor_collector", "htcondor_schedd", "htcondor_config")


class HTCondorJobState(AsynchronousJobState):
    def __init__(
        self,
        job_wrapper: "MinimalJobWrapper",
        job_destination: "JobDestination",
        user_log: str,
        *,
        files_dir=None,
        job_id: Union[str, None] = None,
        job_file=None,
        output_file=None,
        error_file=None,
        exit_code_file=None,
        job_name=None,
    ) -> None:
        """
        Encapsulates state related to a job that is being run via the DRM and
        that we need to monitor.
        """
        super().__init__(
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
        self.failed = False
        self.user_log = user_log
        self.user_log_size = 0
        self._event_log = None

    def event_log(self, htcondor):
        if self._event_log is None:
            self._event_log = htcondor.JobEventLog(self.user_log)
        return self._event_log


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

        condor_config = kwargs.get("htcondor_config")
        if condor_config:
            os.environ.setdefault("CONDOR_CONFIG", condor_config)

        super().__init__(app, nworkers, **kwargs)
        try:
            import htcondor2
        except Exception as exc:
            raise exc.__class__(
                "The htcondor2 Python package is required to use this feature, please install it or correct the "
                f"following error:\n{exc.__class__.__name__}: {str(exc)}"
            )
        self.htcondor = htcondor2
        self._local_schedd = None
        self._schedd_cache = {}
        # Protect schedd initialization/cache in multi-threaded runners.
        self._schedd_lock = threading.Lock()

        if self.runner_params.htcondor_config:
            self._apply_condor_config(self.runner_params.htcondor_config)

    def _apply_condor_config(self, condor_config: Optional[str]) -> None:
        """Set CONDOR_CONFIG and reload htcondor2 config when possible."""
        if not condor_config:
            return
        existing = os.environ.get("CONDOR_CONFIG")
        if existing and existing != condor_config:
            log.warning(
                "CONDOR_CONFIG is already set to %s; ignoring htcondor_config=%s",
                existing,
                condor_config,
            )
            return
        os.environ["CONDOR_CONFIG"] = condor_config
        if hasattr(self, "htcondor"):
            try:
                self.htcondor.reload_config()
            except Exception as exc:
                log.warning("Failed to reload HTCondor config after setting CONDOR_CONFIG: %s", exc)

    def _htcondor_params(self, job_destination: "JobDestination"):
        """Resolve collector/schedd/config parameters from the destination or runner defaults."""
        params = job_destination.params
        collector = params.get("htcondor_collector", None) or self.runner_params.htcondor_collector
        schedd_name = params.get("htcondor_schedd", None) or self.runner_params.htcondor_schedd
        condor_config = params.get("htcondor_config", None) or self.runner_params.htcondor_config
        return collector, schedd_name, condor_config

    def _local_schedd_for_destination(self):
        """Return the local Schedd instance, lazily initialized once."""
        if self._local_schedd is None:
            with self._schedd_lock:
                if self._local_schedd is None:
                    self._local_schedd = self.htcondor.Schedd()
        return self._local_schedd

    def _schedd_for_destination(self, job_destination: "JobDestination"):
        """Locate a Schedd for the destination, caching by collector/schedd/config.

        This supports both local pools and remote collectors. Results are cached
        because the locate calls involve network lookups; a lock protects cache
        access since the runner uses multiple threads.
        """
        collector, schedd_name, condor_config = self._htcondor_params(job_destination)
        self._apply_condor_config(condor_config)

        if not collector and not schedd_name:
            return self._local_schedd_for_destination()

        cache_key = (
            collector,
            schedd_name,
            os.environ.get("CONDOR_CONFIG"),
        )
        with self._schedd_lock:
            cached = self._schedd_cache.get(cache_key)
        if cached:
            return cached

        collector_obj = self.htcondor.Collector(pool=collector) if collector else self.htcondor.Collector()
        if schedd_name:
            schedd_ad = collector_obj.locate(self.htcondor.DaemonType.Schedd, name=schedd_name)
        else:
            schedd_ads = collector_obj.locateAll(self.htcondor.DaemonType.Schedd)
            schedd_ad = schedd_ads[0] if schedd_ads else None
        if not schedd_ad:
            location = f"collector={collector}" if collector else "local collector"
            raise Exception(f"Unable to locate schedd via {location} (schedd={schedd_name or 'first'})")

        schedd = self.htcondor.Schedd(schedd_ad)
        with self._schedd_lock:
            self._schedd_cache[cache_key] = schedd
        return schedd

    def _submit_params(self, job_destination: "JobDestination"):
        """Map destination params to submit params, excluding htcondor_* keys."""
        params = {k: v for k, v in job_destination.params.items() if k not in HTCONDOR_DESTINATION_KEYS}
        return submission_params(prefix="", **params)

    def queue_job(self, job_wrapper: "MinimalJobWrapper") -> None:
        """Create job script and submit it to the DRM."""

        # prepare the job
        include_metadata = asbool(job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
        if not self.prepare_job(job_wrapper, include_metadata=include_metadata):
            return

        job_destination = job_wrapper.job_destination
        galaxy_id_tag = job_wrapper.get_id_tag()

        # get destination params
        query_params = self._submit_params(job_destination)
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

        cjs = HTCondorJobState(
            job_wrapper=job_wrapper,
            job_destination=job_destination,
            user_log=os.path.join(job_wrapper.working_directory, f"galaxy_{galaxy_id_tag}.condor.log"),
            files_dir=job_wrapper.working_directory,
        )
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
        # Write submit description to disk for debugging and parity with the CLI runner,
        # even though submission is performed via the htcondor2 API below.
        try:
            with open(submit_file, "w") as handle:
                handle.write(submit_file_contents)
        except Exception:
            if cleanup_job == "always":
                cjs.cleanup()
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

        try:
            # The htcondor runner targets the htcondor2 API only; no legacy-API fallback is maintained.
            submit_description = self.htcondor.Submit(submit_file_contents)
            schedd = self._schedd_for_destination(job_destination)
            submit_result = schedd.submit(submit_description)
            external_job_id = str(submit_result.cluster())
        except Exception:
            log.exception("htcondor submit failed for job %s", job_wrapper.get_id_tag())
            if self.app.config.cleanup_job == "always" and os.path.exists(submit_file):
                os.unlink(submit_file)
                cjs.cleanup()
            job_wrapper.fail("htcondor submit failed", exception=True)
            return

        if os.path.exists(submit_file):
            os.unlink(submit_file)

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
                assert cjs.job_wrapper.tool is not None
                if cjs.job_wrapper.tool.tool_type != "interactive":
                    try:
                        log_size = os.stat(cjs.user_log).st_size
                        if log_size == cjs.user_log_size:
                            new_watched.append(cjs)
                            continue
                    except FileNotFoundError:
                        new_watched.append(cjs)
                        continue

                job_running, job_complete, job_failed, job_held, log_size = self._summarize_event_log(cjs)
                cjs.user_log_size = log_size
            except Exception:
                log.exception(f"({galaxy_id_tag}/{job_id}) Unable to check job status")
                log.warning(f"({galaxy_id_tag}/{job_id}) job will now be errored")
                cjs.fail_message = "Cluster could not complete job"
                self.work_queue.put((self.fail_job, cjs))
                continue

            if job_running:
                cjs.job_wrapper.check_for_entry_points()

            if job_running and not cjs.running:
                log.debug(f"({galaxy_id_tag}/{job_id}) job is now running")
                cjs.job_wrapper.change_state(model.Job.states.RUNNING)
            if not job_running and cjs.running:
                log.debug(f"({galaxy_id_tag}/{job_id}) job has stopped running")

            job_state = cjs.job_wrapper.get_state()
            if job_held:
                # Keep the job queued for now; HTCondor hold handling needs discussion.
                if job_state not in (model.Job.states.DELETED, model.Job.states.STOPPED):
                    cjs.job_wrapper.change_state(model.Job.states.QUEUED)
                cjs.running = False
                new_watched.append(cjs)
                continue
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
            cjs.running = job_running
            new_watched.append(cjs)
        self.watched = new_watched

    def stop_job(self, job_wrapper):
        """Attempts to delete a job from the DRM queue."""
        job = job_wrapper.get_job()
        external_id = job.job_runner_external_id
        galaxy_id_tag = job_wrapper.get_id_tag()
        if job.container:
            try:
                log.info(f"stop_job(): {job.id}: trying to stop container .... ({external_id})")
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
                if cjs and cjs.job_wrapper.get_state() != model.Job.states.DELETED:
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
                    failure_message = self._condor_remove(external_id, job_wrapper.job_destination)
                    if failure_message:
                        log.debug(f"({external_id}). Failed to stop condor {failure_message}")
        else:
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
        job_running = cjs.running
        job_complete = False
        job_failed = False
        job_held = False

        cluster_id = int(cjs.job_id)
        log_size = os.path.getsize(cjs.user_log)
        event_log = cjs.event_log(self.htcondor)

        for event in event_log.events(stop_after=0):
            if event.cluster != cluster_id or event.proc != 0:
                continue
            event_type = event.type
            if event_type == self.htcondor.JobEventType.EXECUTE:
                job_running = True
            elif event_type in (
                self.htcondor.JobEventType.JOB_EVICTED,
                self.htcondor.JobEventType.JOB_SUSPENDED,
            ):
                job_running = False
            elif event_type == self.htcondor.JobEventType.JOB_TERMINATED:
                job_complete = True
            elif event_type == self.htcondor.JobEventType.JOB_HELD:
                # Keep jobs in the queue on hold for now; behavior needs discussion.
                job_running = False
                job_held = True
            elif event_type in (
                self.htcondor.JobEventType.JOB_ABORTED,
                self.htcondor.JobEventType.CLUSTER_REMOVE,
            ):
                job_failed = True

        return job_running, job_complete, job_failed, job_held, log_size

    def _condor_remove(self, external_id, job_destination: Optional["JobDestination"] = None):
        if not external_id:
            return "Missing external job id"
        try:
            job_id = int(external_id)
        except Exception:
            job_id = external_id
        try:
            schedd = (
                self._schedd_for_destination(job_destination)
                if job_destination is not None
                else self._local_schedd_for_destination()
            )
            schedd.act(self.htcondor.JobAction.Remove, job_id, reason="Galaxy job stop request")
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
        log.debug("_run_command(%s) exit code (%s) and failure: %s", command, exit_code, stderr)
        return (exit_code, ret)

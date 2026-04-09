"""Job control via the HTCondor DRM using the htcondor2 Python API."""

import json
import logging
import os
import subprocess
import sys
import threading
from typing import (
    Optional,
    TYPE_CHECKING,
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
HTCONDOR_HELPER_MODULE = "galaxy.jobs.runners.htcondor_helper"
HTCONDOR_HELPER_TIMEOUT = 5


def _normalize_condor_config(condor_config: Optional[str]) -> Optional[str]:
    if not condor_config:
        return None
    return os.path.realpath(os.path.expanduser(condor_config))


def _locate_schedd(htcondor, schedd_cache, schedd_lock, collector: Optional[str], schedd_name: Optional[str]):
    cache_key = (collector, schedd_name)
    with schedd_lock:
        cached = schedd_cache.get(cache_key)
    if cached:
        return cached

    if not collector and not schedd_name:
        schedd = htcondor.Schedd()
    else:
        collector_obj = htcondor.Collector(pool=collector) if collector else htcondor.Collector()
        if schedd_name:
            schedd_ad = collector_obj.locate(htcondor.DaemonType.Schedd, name=schedd_name)
        else:
            schedd_ads = collector_obj.locateAll(htcondor.DaemonType.Schedd)
            schedd_ad = schedd_ads[0] if schedd_ads else None
        if not schedd_ad:
            location = f"collector={collector}" if collector else "local collector"
            raise RuntimeError(f"Unable to locate schedd via {location} (schedd={schedd_name or 'first'})")
        schedd = htcondor.Schedd(schedd_ad)

    with schedd_lock:
        schedd_cache[cache_key] = schedd
    return schedd


class _HTCondorClient:
    def submit(self, submit_description: str, collector: Optional[str], schedd_name: Optional[str]) -> str:
        raise NotImplementedError()

    def remove(self, job_spec: Union[int, str], collector: Optional[str], schedd_name: Optional[str]) -> None:
        raise NotImplementedError()

    def shutdown(self) -> None:
        pass


class _HTCondorInProcessClient(_HTCondorClient):
    def __init__(self, htcondor):
        self.htcondor = htcondor
        self._schedd_cache = {}
        self._schedd_lock = threading.Lock()

    def _schedd(self, collector: Optional[str], schedd_name: Optional[str]):
        return _locate_schedd(self.htcondor, self._schedd_cache, self._schedd_lock, collector, schedd_name)

    def submit(self, submit_description: str, collector: Optional[str], schedd_name: Optional[str]) -> str:
        submit_result = self._schedd(collector, schedd_name).submit(self.htcondor.Submit(submit_description))
        return str(submit_result.cluster())

    def remove(self, job_spec: Union[int, str], collector: Optional[str], schedd_name: Optional[str]) -> None:
        self._schedd(collector, schedd_name).act(
            self.htcondor.JobAction.Remove, job_spec, reason="Galaxy job stop request"
        )


class _HTCondorSubprocessClient(_HTCondorClient):
    def __init__(self, condor_config: str):
        self.condor_config = condor_config
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    def submit(self, submit_description: str, collector: Optional[str], schedd_name: Optional[str]) -> str:
        response = self._request(
            dict(
                command="submit",
                collector=collector,
                schedd_name=schedd_name,
                submit_description=submit_description,
            )
        )
        return str(response["cluster"])

    def remove(self, job_spec: Union[int, str], collector: Optional[str], schedd_name: Optional[str]) -> None:
        self._request(
            dict(
                command="remove",
                collector=collector,
                schedd_name=schedd_name,
                job_spec=job_spec,
            )
        )

    def shutdown(self) -> None:
        with self._lock:
            process = self._process
            if process is None:
                return
            try:
                stdin = process.stdin
                if stdin is not None and not stdin.closed:
                    stdin.write(json.dumps(dict(command="shutdown")) + "\n")
                    stdin.flush()
            except Exception:
                pass
            finally:
                if process.stdin is not None and not process.stdin.closed:
                    process.stdin.close()

            try:
                process.wait(timeout=HTCONDOR_HELPER_TIMEOUT)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=HTCONDOR_HELPER_TIMEOUT)
            finally:
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()
                self._process = None

    def _request(self, payload):
        with self._lock:
            process = self._ensure_process_locked()
            stdin = process.stdin
            stdout = process.stdout
            if stdin is None or stdout is None:
                raise RuntimeError("HTCondor helper process is missing stdio pipes")
            try:
                stdin.write(json.dumps(payload) + "\n")
                stdin.flush()
            except Exception as exc:
                raise RuntimeError(self._helper_failure_message_locked("Failed to write to HTCondor helper")) from exc

            line = stdout.readline()
            if not line:
                raise RuntimeError(self._helper_failure_message_locked("HTCondor helper exited unexpectedly"))
            try:
                response = json.loads(line)
            except Exception as exc:
                raise RuntimeError(f"Invalid response from HTCondor helper: {line.rstrip()}") from exc
            if not response.get("ok"):
                raise RuntimeError(response.get("error", "Unknown HTCondor helper error"))
            return response

    def _ensure_process_locked(self):
        process = self._process
        if process is not None and process.poll() is None:
            return process
        if process is not None:
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()

        env = os.environ.copy()
        env["CONDOR_CONFIG"] = self.condor_config
        env.setdefault("PYTHONUNBUFFERED", "1")
        env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(path for path in sys.path if path))
        self._process = subprocess.Popen(
            [sys.executable, "-m", HTCONDOR_HELPER_MODULE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            close_fds=True,
            env=env,
        )
        return self._process

    def _helper_failure_message_locked(self, message: str) -> str:
        process = self._process
        if process is None or process.stderr is None or process.poll() is None:
            return message
        stderr = process.stderr.read().strip()
        if stderr:
            return f"{message}: {stderr}"
        return message


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

        super().__init__(app, nworkers, **kwargs)
        try:
            import htcondor2
        except Exception as exc:
            raise exc.__class__(
                "The htcondor2 Python package is required to use this feature, please install it or correct the "
                f"following error:\n{exc.__class__.__name__}: {str(exc)}"
            )
        self.htcondor = htcondor2
        self._client_cache = {}
        self._client_lock = threading.Lock()

    def shutdown(self):
        try:
            super().shutdown()
        finally:
            self._shutdown_clients()

    def _shutdown_clients(self) -> None:
        with self._client_lock:
            clients = list(self._client_cache.values())
            self._client_cache.clear()
        for client in clients:
            try:
                client.shutdown()
            except Exception:
                log.exception("Failed to shut down HTCondor client")

    def _htcondor_params(self, job_destination: Optional["JobDestination"]):
        """Resolve collector/schedd/config parameters from the destination or runner defaults."""
        params = job_destination.params if job_destination is not None else {}
        collector = params.get("htcondor_collector", None) or self.runner_params.htcondor_collector
        schedd_name = params.get("htcondor_schedd", None) or self.runner_params.htcondor_schedd
        condor_config = params.get("htcondor_config", None) or self.runner_params.htcondor_config
        return collector, schedd_name, _normalize_condor_config(condor_config)

    def _client_for_destination(self, job_destination: Optional["JobDestination"]):
        _, _, condor_config = self._htcondor_params(job_destination)
        with self._client_lock:
            client = self._client_cache.get(condor_config)
            if client is None:
                if condor_config is None:
                    client = _HTCondorInProcessClient(self.htcondor)
                else:
                    client = _HTCondorSubprocessClient(condor_config)
                self._client_cache[condor_config] = client
        return client

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
        try:
            with open(submit_file, "w") as handle:
                handle.write(submit_file_contents)
        except Exception:
            if cleanup_job == "always":
                cjs.cleanup()
            job_wrapper.fail("failure preparing submit file", exception=True)
            log.exception(f"({galaxy_id_tag}) failure preparing submit file")
            return

        if job_wrapper.get_state() in (model.Job.states.DELETED, model.Job.states.STOPPED):
            log.debug("(%s) Job deleted/stopped by user before it entered the queue", galaxy_id_tag)
            if cleanup_job in ("always", "onsuccess"):
                os.unlink(submit_file)
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
            if job_held:
                if job_state not in (model.Job.states.DELETED, model.Job.states.STOPPED):
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

        if cjs.job_id is None:
            raise RuntimeError("Missing HTCondor job_id while summarizing event log.")
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
            job_spec: Union[int, str] = int(external_id)
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

"""Job control via the HTCondor DRM using the htcondor2 Python API.

See the Galaxy cluster documentation (doc/source/admin/cluster.md) for
configuration, architecture details, and testing instructions.
"""

import json
import logging
import os
import select
import shlex
import subprocess
import sys
import threading
from collections import deque
from typing import (
    Any,
    NamedTuple,
    TYPE_CHECKING,
)

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.jobs.runners.htcondor_helper import _locate_schedd
from galaxy.jobs.runners.util import runner_states
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

HTCONDOR_DESTINATION_KEYS = (
    "htcondor_collector",
    "htcondor_schedd",
    "htcondor_config",
    "request_walltime",
    "max_held_count",
    "embed_metadata_in_job",
)
HTCONDOR_HELPER_MODULE = "galaxy.jobs.runners.htcondor_helper"
HTCONDOR_HELPER_TIMEOUT = 30
# Number of consecutive status-check errors before a job is failed.  A small
# count absorbs transient filesystem hiccups (e.g. NFS timeouts reading the
# event log) without masking genuine persistent failures.
MAX_STATUS_ERROR_COUNT = 3
# Number of consecutive monitor cycles in which the event log is absent before
# a job is failed.  Covers the case where the log was never written (e.g.
# filesystem full at submit time) or was lost after Galaxy restarted.
MAX_MISSING_LOG_COUNT = 5

# HTCondor HoldReasonCode values that indicate the job was held because it
# exceeded its memory allocation.  Code 26 is the cgroup-based OOM code used in
# older HTCondor releases; code 34 ("memory limit exceeded") was introduced in
# newer releases (~9.x).  Both are defined in condor_holdcodes.h in the HTCondor
# source tree.  If your cluster reports a different code for OOM holds, add it
# here and open a PR.
_HOLD_CODE_MEMORY = frozenset((26, 34))
# Code 16 ("PeriodicHoldTrue") means a periodic_hold ClassAd expression evaluated
# to True.  This code has been stable since at least HTCondor 7.x.  Galaxy injects
# "periodic_hold = (JobDurationSeconds >= N)" when request_walltime is set.
_HOLD_CODE_PERIODIC = 16
# SIGKILL from the OS OOM killer appears as a JOB_TERMINATED event with
# TerminatedNormally=False and TermSignal=9.
_SIGKILL = 9

_MEMORY_LIMIT_HOLD_MSG = (
    "This job was held by HTCondor because it exceeded its requested memory. "
    "Consider increasing request_memory or routing to a destination with more memory."
)
_WALLTIME_HOLD_MSG = (
    "This job was held by HTCondor because it exceeded its maximum run time. "
    "Consider increasing the walltime or routing to a destination with a longer time limit."
)
_SIGKILL_MSG = (
    "This job was killed because it used more memory than it was allocated. Consider increasing request_memory."
)


class _EventLogSummary(NamedTuple):
    job_running: bool
    job_complete: bool
    failure_event: int | None
    job_held: bool
    term_signal: int | None  # signal that killed the process (e.g. 9), None if normal exit
    hold_reason_code: int  # HoldReasonCode from JOB_HELD ClassAd, 0 if absent
    log_missing: bool = False  # True when the event log file does not exist
    job_released: bool = False  # True when a JOB_RELEASED event was seen this cycle


def _parse_memory_mb(value: str) -> int | None:
    """Parse an HTCondor request_memory value to whole MB.

    HTCondor's default unit is MB.  Recognises the K/M/G/T suffixes (case-
    insensitive) and their two-letter forms (KB/MB/GB/TB).  Returns None for
    values that cannot be parsed (e.g. ClassAd expressions).
    """
    value = value.strip()
    _UNITS: dict[str, float] = {"K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}
    upper = value.upper()
    for suffix, factor in _UNITS.items():
        for variant in (suffix + "B", suffix):
            if upper.endswith(variant):
                numeric = value[: -len(variant)]
                try:
                    return max(1, int(float(numeric) * factor))
                except ValueError:
                    return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _parse_walltime_seconds(value: str) -> int | None:
    """Parse a walltime string to a whole number of seconds.

    Accepted formats (matching SLURM's --time convention):
      seconds          "3600"
      MM:SS            "90:00"
      HH:MM:SS         "1:00:00"
      D-HH:MM:SS       "1-0:00:00"

    Returns None if the value cannot be parsed.
    """
    value = value.strip()
    days = 0
    if "-" in value:
        day_part, value = value.split("-", 1)
        try:
            days = int(day_part)
        except ValueError:
            return None
    parts = value.split(":")
    try:
        if len(parts) == 1:
            return days * 86400 + int(parts[0])
        if len(parts) == 2:
            return days * 86400 + int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return days * 86400 + int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return None


def _normalize_condor_config(condor_config: str | None) -> str | None:
    if not condor_config:
        return None
    return os.path.realpath(os.path.expanduser(condor_config))


class _HTCondorClient:
    def submit(self, submit_description: str, collector: str | None, schedd_name: str | None) -> str:
        raise NotImplementedError()

    def remove(self, job_spec: int | str, collector: str | None, schedd_name: str | None) -> None:
        raise NotImplementedError()

    def shutdown(self) -> None:
        pass


class _HTCondorInProcessClient(_HTCondorClient):
    def __init__(self, htcondor):
        self.htcondor = htcondor
        self._schedd_cache: dict = {}
        self._schedd_lock = threading.Lock()

    def _schedd(self, collector: str | None, schedd_name: str | None):
        return _locate_schedd(self.htcondor, self._schedd_cache, self._schedd_lock, collector, schedd_name)

    def _evict_schedd(self, collector: str | None, schedd_name: str | None) -> None:
        with self._schedd_lock:
            self._schedd_cache.pop((collector, schedd_name), None)

    def submit(self, submit_description: str, collector: str | None, schedd_name: str | None) -> str:
        try:
            submit_result = self._schedd(collector, schedd_name).submit(self.htcondor.Submit(submit_description))
            return str(submit_result.cluster())
        except Exception:
            self._evict_schedd(collector, schedd_name)
            raise

    def remove(self, job_spec: int | str, collector: str | None, schedd_name: str | None) -> None:
        try:
            self._schedd(collector, schedd_name).act(
                self.htcondor.JobAction.Remove, job_spec, reason="Galaxy job stop request"
            )
        except Exception:
            self._evict_schedd(collector, schedd_name)
            raise


class _HTCondorSubprocessClient(_HTCondorClient):
    def __init__(self, condor_config: str):
        self.condor_config = condor_config
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        # Rolling buffer of recent stderr lines for error messages.
        # Written by the drain thread; read (without the lock) in error paths.
        self._stderr_lines: deque = deque(maxlen=50)

    def submit(self, submit_description: str, collector: str | None, schedd_name: str | None) -> str:
        response = self._request(
            dict(
                command="submit",
                collector=collector,
                schedd_name=schedd_name,
                submit_description=submit_description,
            )
        )
        return str(response["cluster"])

    def remove(self, job_spec: int | str, collector: str | None, schedd_name: str | None) -> None:
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

            ready, _, _ = select.select([stdout], [], [], HTCONDOR_HELPER_TIMEOUT)
            if not ready:
                self._terminate_process_locked(process)
                raise RuntimeError(
                    f"HTCondor helper did not respond within {HTCONDOR_HELPER_TIMEOUT}s — killed and will respawn"
                )
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

    def _terminate_process_locked(self, process: "subprocess.Popen[str]") -> None:
        """Kill a stale/hung helper process and clean up its pipes. Must be called with self._lock held."""
        try:
            process.kill()
            process.wait(timeout=5)
        except Exception:
            pass
        finally:
            for pipe in (process.stdin, process.stdout, process.stderr):
                if pipe is not None:
                    try:
                        pipe.close()
                    except Exception:
                        pass
            if self._process is process:
                self._process = None

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
        # Build PYTHONPATH from sys.path, then append any entries from the existing
        # PYTHONPATH that are not already present (e.g. paths added only via env var).
        sys_paths = list(dict.fromkeys(path for path in sys.path if path))
        for p in os.environ.get("PYTHONPATH", "").split(os.pathsep):
            if p and p not in sys_paths:
                sys_paths.append(p)
        env["PYTHONPATH"] = os.pathsep.join(sys_paths)
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
        self._start_stderr_drain(self._process)
        return self._process

    def _start_stderr_drain(self, process: "subprocess.Popen[str]") -> None:
        """Drain the helper's stderr into _stderr_lines and the Galaxy log.

        Runs as a daemon thread so HTCondor warnings (e.g. credential expiry)
        surface in Galaxy's log rather than being silently discarded.
        """

        def _drain() -> None:
            try:
                for line in process.stderr:  # type: ignore[union-attr]
                    stripped = line.rstrip()
                    if stripped:
                        self._stderr_lines.append(stripped)
                        log.warning("HTCondor helper: %s", stripped)
            except Exception:
                pass

        t = threading.Thread(target=_drain, daemon=True, name="htcondor-helper-stderr")
        t.start()

    def _helper_failure_message_locked(self, message: str) -> str:
        # Stderr is consumed by the drain thread and buffered in _stderr_lines.
        recent = "\n".join(list(self._stderr_lines)[-10:]).strip()
        if recent:
            return f"{message}: {recent}"
        return message


class HTCondorJobState(AsynchronousJobState):
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
        self._event_log: Any = None
        self.status_error_count = 0
        self.held_count = 0
        self.missing_log_count = 0

    def event_log(self, htcondor):
        if self._event_log is None:
            self._event_log = htcondor.JobEventLog(self.user_log)
        return self._event_log

    def close_event_log(self) -> None:
        if self._event_log is not None:
            try:
                self._event_log.close()
            except Exception:
                pass
            self._event_log = None


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
            raise ImportError(
                "The htcondor2 Python package is required to use this feature, please install it or correct the "
                f"following error:\n{exc.__class__.__name__}: {str(exc)}"
            ) from exc
        self.htcondor = htcondor2
        self._client_cache: dict = {}
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

    def _htcondor_params(self, job_destination: "JobDestination | None"):
        """Resolve collector/schedd/config parameters from the destination or runner defaults."""
        params = job_destination.params if job_destination is not None else {}
        collector = params.get("htcondor_collector", None) or self.runner_params.htcondor_collector
        schedd_name = params.get("htcondor_schedd", None) or self.runner_params.htcondor_schedd
        condor_config = params.get("htcondor_config", None) or self.runner_params.htcondor_config
        return collector, schedd_name, _normalize_condor_config(condor_config)

    def _client_for_destination(self, job_destination: "JobDestination | None"):
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
            memory_mb = _parse_memory_mb(str(request_memory))
            if memory_mb is not None:
                slots = int(query_params.get("request_cpus", 1) or 1)
                per_slot = memory_mb // max(1, slots)
                galaxy_memory_statement = (
                    f'GALAXY_MEMORY_MB="{memory_mb}"; export GALAXY_MEMORY_MB; '
                    f'GALAXY_MEMORY_MB_PER_SLOT="{per_slot}"; export GALAXY_MEMORY_MB_PER_SLOT;'
                )

        if request_walltime := job_destination.params.get("request_walltime", None):
            walltime_seconds = _parse_walltime_seconds(str(request_walltime))
            if walltime_seconds is not None and "periodic_hold" not in query_params:
                query_params["periodic_hold"] = f"(JobDurationSeconds >= {walltime_seconds})"

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
                cjs.status_error_count = 0
            except Exception:
                cjs.status_error_count += 1
                if cjs.status_error_count < MAX_STATUS_ERROR_COUNT:
                    log.warning(
                        f"({galaxy_id_tag}/{job_id}) Transient error checking job status "
                        f"(attempt {cjs.status_error_count}/{MAX_STATUS_ERROR_COUNT}), "
                        "will retry next cycle"
                    )
                    new_watched.append(cjs)
                    continue
                log.exception(f"({galaxy_id_tag}/{job_id}) Unable to check job status")
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
                cjs.missing_log_count += 1
                if cjs.missing_log_count >= MAX_MISSING_LOG_COUNT:
                    log.warning(
                        f"({galaxy_id_tag}/{job_id}) event log absent for "
                        f"{cjs.missing_log_count} consecutive cycles, failing job"
                    )
                    cjs.fail_message = (
                        "This job's HTCondor event log could not be found. "
                        "Galaxy cannot determine the job outcome — the job may have "
                        "been removed from the queue while Galaxy was unavailable."
                    )
                    cjs.runner_state = runner_states.UNKNOWN_ERROR
                    cjs.close_event_log()
                    self.work_queue.put((self.fail_job, cjs))
                    continue
                log.debug(
                    f"({galaxy_id_tag}/{job_id}) event log not yet available "
                    f"(cycle {cjs.missing_log_count}/{MAX_MISSING_LOG_COUNT})"
                )
                new_watched.append(cjs)
                continue
            cjs.missing_log_count = 0

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
                    if term_signal == _SIGKILL and job_state != model.Job.states.STOPPED:
                        log.info(f"({galaxy_id_tag}/{job_id}) job killed by signal 9, likely OOM")
                        cjs.fail_message = _SIGKILL_MSG
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
                    if hold_reason_code in _HOLD_CODE_MEMORY:
                        log.info(
                            f"({galaxy_id_tag}/{job_id}) job held for memory limit "
                            f"(HoldReasonCode={hold_reason_code})"
                        )
                        cjs.fail_message = _MEMORY_LIMIT_HOLD_MSG
                        cjs.runner_state = runner_states.MEMORY_LIMIT_REACHED
                        cjs.close_event_log()
                        self.work_queue.put((self.fail_job, cjs))
                        continue
                    if hold_reason_code == _HOLD_CODE_PERIODIC:
                        log.info(f"({galaxy_id_tag}/{job_id}) job held by periodic_hold expression (walltime)")
                        cjs.fail_message = _WALLTIME_HOLD_MSG
                        cjs.runner_state = runner_states.WALLTIME_REACHED
                        cjs.close_event_log()
                        self.work_queue.put((self.fail_job, cjs))
                        continue
                    cjs.held_count += 1
                    # max_held_count: destination parameter, counts distinct JOB_HELD events (default 3, 0 = disabled)
                    max_held_count = int(cjs.job_wrapper.job_destination.params.get("max_held_count", 3))
                    if max_held_count > 0 and cjs.held_count >= max_held_count:
                        log.warning(
                            f"({galaxy_id_tag}/{job_id}) Job held {cjs.held_count} "
                            "times without release, failing permanently"
                        )
                        cjs.fail_message = (
                            f"This job was held by HTCondor {cjs.held_count} time"
                            f"{'s' if cjs.held_count != 1 else ''} without being released."
                        )
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

    def _summarize_event_log(self, cjs: HTCondorJobState) -> _EventLogSummary:
        job_running = cjs.running
        job_complete = False
        failure_event: int | None = None
        job_held = False
        term_signal: int | None = None
        hold_reason_code: int = 0

        if cjs.job_id is None:
            raise RuntimeError("Missing HTCondor job_id while summarizing event log.")
        cluster_id = int(cjs.job_id)

        if not os.path.exists(cjs.user_log):
            return _EventLogSummary(cjs.running, False, None, False, None, 0, log_missing=True)

        event_log = cjs.event_log(self.htcondor)
        job_released = False

        for event in event_log.events(stop_after=0):
            if event.cluster != cluster_id or event.proc != 0:
                continue
            event_type = event.type
            if event_type == self.htcondor.JobEventType.EXECUTE:
                job_running = True
                job_held = False
            elif event_type in (
                self.htcondor.JobEventType.JOB_EVICTED,
                self.htcondor.JobEventType.JOB_SUSPENDED,
            ):
                job_running = False
            elif event_type == self.htcondor.JobEventType.JOB_UNSUSPENDED:
                job_running = True
            elif event_type == self.htcondor.JobEventType.JOB_TERMINATED:
                job_complete = True
                if not event.get("TerminatedNormally", True):
                    term_signal = int(event.get("TermSignal", 0)) or None
            elif event_type == self.htcondor.JobEventType.JOB_HELD:
                job_running = False
                job_held = True
                hold_reason_code = int(event.get("HoldReasonCode", 0))
            elif event_type == self.htcondor.JobEventType.JOB_RELEASED:
                job_held = False
                job_running = False
                hold_reason_code = 0
                job_released = True
            elif event_type in (
                self.htcondor.JobEventType.JOB_ABORTED,
                self.htcondor.JobEventType.CLUSTER_REMOVE,
                self.htcondor.JobEventType.SHADOW_EXCEPTION,
                self.htcondor.JobEventType.EXECUTABLE_ERROR,
            ):
                failure_event = event_type

        return _EventLogSummary(
            job_running,
            job_complete,
            failure_event,
            job_held,
            term_signal,
            hold_reason_code,
            job_released=job_released,
        )

    def _apply_failure_event(self, cjs: HTCondorJobState, failure_event: int) -> None:
        """Set fail_message and runner_state on cjs based on the HTCondor failure event type."""
        htc = self.htcondor.JobEventType
        if failure_event == htc.SHADOW_EXCEPTION:
            cjs.fail_message = (
                "This job failed due to an HTCondor shadow exception, which typically "
                "indicates a transient error in the execution environment."
            )
            cjs.runner_state = runner_states.UNKNOWN_ERROR
        elif failure_event == htc.JOB_ABORTED:
            cjs.fail_message = "This job was removed from the HTCondor queue."
            cjs.runner_state = runner_states.UNKNOWN_ERROR
        elif failure_event == htc.CLUSTER_REMOVE:
            cjs.fail_message = "The HTCondor cluster was removed."
            cjs.runner_state = runner_states.UNKNOWN_ERROR
        elif failure_event == htc.EXECUTABLE_ERROR:
            # Executable errors are configuration problems, not transient.  runner_state is
            # intentionally left unset (None) so the resubmission framework never fires for
            # this case — only UNKNOWN_ERROR triggers resubmission handlers.
            cjs.fail_message = "This job could not start because the job script could not be found or executed."
        else:
            cjs.fail_message = "Cluster could not complete job"
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

"""HTCondor support built on the htcondor2 (Python bindings version 2) API.

This module should contain functionality shared between Galaxy and the Pulsar.
It deliberately knows nothing about either application's job model — callers
map the vocabulary defined here (``EventLogSummary``, the ``HOLD_REASON_*`` and
``FAILURE_*`` keys) onto their own job states.

``from __future__ import annotations`` is required: Pulsar still supports
Python 3.7, so the ``X | None`` annotations below must not be evaluated at
runtime.  For the same reason this module must avoid the walrus operator and
any other syntax newer than 3.7.
"""

from __future__ import annotations

import json
import logging
import os
import select
import subprocess
import sys
import threading
import time
from collections import deque
from typing import (
    Any,
    NamedTuple,
)

from .htcondor_helper import locate_schedd

log = logging.getLogger(__name__)

__all__ = (
    "EventLogSummary",
    "HTCondorClient",
    "HTCondorClientCache",
    "HTCondorEventLogTracker",
    "HTCondorInProcessClient",
    "HTCondorSubprocessClient",
    "classify_failure_event",
    "classify_hold",
    "held_message",
    "import_htcondor",
    "normalize_condor_config",
    "parse_memory_mb",
    "parse_walltime_seconds",
    "periodic_hold_expression",
)

# Resolved against whichever package root loaded this module so that the helper
# subprocess can be started as ``python -m <module>`` from either Galaxy
# (galaxy.jobs.runners.util.condor) or Pulsar (pulsar.managers.util.condor).
HTCONDOR_HELPER_MODULE = f"{__package__}.htcondor_helper"
HTCONDOR_HELPER_TIMEOUT = 30
DEFAULT_REMOVE_REASON = "Job stop request"

# Escalation thresholds for conditions that are usually transient.  These are
# wall-clock seconds rather than poll counts because the polling interval is
# configurable in both applications (and a Pulsar job is polled by both the
# Pulsar monitor and Galaxy), so a count of cycles has no fixed meaning.
#
# How long status checks may keep failing - absorbs transient filesystem
# hiccups (e.g. NFS timeouts reading the event log) without masking genuine
# persistent failures.
STATUS_ERROR_GRACE_SECONDS = 30.0
# How long the event log may be absent.  Covers a log not yet visible after
# submission (NFS attribute caching defaults to 60s) as well as one that was
# never written or was lost while the application was down.
MISSING_LOG_GRACE_SECONDS = 60.0
# How long a job may sit held before it is failed.  A hold is not by itself
# terminal: a pool may release the job on its own, and sites commonly configure
# periodic_release to retry a held job - sometimes against a raised
# request_memory, so that the retry can succeed where the first attempt was
# held.  Failing on the hold reason alone would pre-empt that policy, so the
# job is failed only once it has stayed held for this long without a release.
HELD_GRACE_SECONDS = 300.0
# Number of distinct JOB_HELD events tolerated before a job is failed
# permanently.  This bounds hold/release thrashing, which the grace window
# above cannot catch because each release restarts it.  0 disables the
# escalation.
DEFAULT_MAX_HELD_COUNT = 3

# HTCondor HoldReasonCode values that indicate the job was held because it
# exceeded its memory allocation.  Code 26 is the cgroup-based OOM code used in
# older HTCondor releases; code 34 ("memory limit exceeded") was introduced in
# newer releases (~9.x).  Both are defined in condor_holdcodes.h in the HTCondor
# source tree.  If your cluster reports a different code for OOM holds, add it
# here and open a PR.
HOLD_CODE_MEMORY = frozenset((26, 34))
# Code 16 ("PeriodicHoldTrue") means a periodic_hold ClassAd expression evaluated
# to True.  This code has been stable since at least HTCondor 7.x.  Callers inject
# "periodic_hold = (JobDurationSeconds >= N)" when a walltime is requested.
HOLD_CODE_PERIODIC = 16
# SIGKILL from the OS OOM killer appears as a JOB_TERMINATED event with
# TerminatedNormally=False and TermSignal=9.
SIGKILL = 9

HOLD_REASON_MEMORY_LIMIT = "memory_limit"
HOLD_REASON_WALLTIME = "walltime"
HOLD_REASON_OTHER = "other"

FAILURE_SHADOW_EXCEPTION = "shadow_exception"
FAILURE_JOB_ABORTED = "job_aborted"
FAILURE_CLUSTER_REMOVED = "cluster_removed"
FAILURE_EXECUTABLE_ERROR = "executable_error"
FAILURE_UNKNOWN = "unknown"

MEMORY_LIMIT_HOLD_MESSAGE = (
    "This job was held by HTCondor because it exceeded its requested memory. "
    "Consider increasing request_memory or routing to a destination with more memory."
)
WALLTIME_HOLD_MESSAGE = (
    "This job was held by HTCondor because it exceeded its maximum run time. "
    "Consider increasing the walltime or routing to a destination with a longer time limit."
)
SIGKILL_MESSAGE = (
    "This job was killed because it used more memory than it was allocated. Consider increasing request_memory."
)
MISSING_LOG_MESSAGE = (
    "This job's HTCondor event log could not be found. The job outcome cannot be "
    "determined — the job may have been removed from the queue while the job "
    "manager was unavailable."
)
UNKNOWN_FAILURE_MESSAGE = "Cluster could not complete job"

HELD_TOO_LONG_MESSAGE = (
    "This job was held by HTCondor and stayed held without being released. "
    "It may be waiting on a resource the pool cannot satisfy."
)

HOLD_MESSAGES = {
    HOLD_REASON_MEMORY_LIMIT: MEMORY_LIMIT_HOLD_MESSAGE,
    HOLD_REASON_WALLTIME: WALLTIME_HOLD_MESSAGE,
}

FAILURE_MESSAGES = {
    FAILURE_SHADOW_EXCEPTION: (
        "This job failed due to an HTCondor shadow exception, which typically "
        "indicates a transient error in the execution environment."
    ),
    FAILURE_JOB_ABORTED: "This job was removed from the HTCondor queue.",
    FAILURE_CLUSTER_REMOVED: "The HTCondor cluster was removed.",
    FAILURE_EXECUTABLE_ERROR: "This job could not start because the job script could not be found or executed.",
    FAILURE_UNKNOWN: UNKNOWN_FAILURE_MESSAGE,
}


def import_htcondor():
    """Import and return the htcondor2 module, raising a helpful ImportError."""
    try:
        import htcondor2
    except Exception as exc:
        raise ImportError(
            "The htcondor2 Python package is required to use this feature, please install it or correct the "
            f"following error:\n{exc.__class__.__name__}: {str(exc)}"
        ) from exc
    return htcondor2


def held_message(held_count: int) -> str:
    plural = "s" if held_count != 1 else ""
    return f"This job was held by HTCondor {held_count} time{plural} without being released."


def parse_memory_mb(value: str) -> int | None:
    """Parse an HTCondor request_memory value to whole MB.

    HTCondor's default unit is MB.  Recognises the K/M/G/T suffixes (case-
    insensitive) and their two-letter forms (KB/MB/GB/TB).  Returns None for
    values that cannot be parsed (e.g. ClassAd expressions).

    >>> parse_memory_mb("2048")
    2048
    >>> parse_memory_mb("4 GB")
    4096
    >>> parse_memory_mb("(Target.Memory)") is None
    True
    """
    value = value.strip()
    units: dict[str, float] = {"K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}
    upper = value.upper()
    for suffix, factor in units.items():
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


def parse_walltime_seconds(value: str) -> int | None:
    """Parse a walltime string to a whole number of seconds.

    Accepted formats (matching SLURM's --time convention):
      seconds          "3600"
      MM:SS            "90:00"
      HH:MM:SS         "1:00:00"
      D-HH:MM:SS       "1-0:00:00"

    Returns None if the value cannot be parsed.

    >>> parse_walltime_seconds("90:00")
    5400
    >>> parse_walltime_seconds("1-0:00:00")
    86400
    >>> parse_walltime_seconds("forever") is None
    True
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


def periodic_hold_expression(walltime_seconds: int) -> str:
    """ClassAd expression holding a job once it has run for walltime_seconds."""
    return f"(JobDurationSeconds >= {walltime_seconds})"


def normalize_condor_config(condor_config: str | None) -> str | None:
    if not condor_config:
        return None
    return os.path.realpath(os.path.expanduser(condor_config))


def classify_hold(hold_reason_code: int) -> str:
    """Map an HTCondor HoldReasonCode onto one of the HOLD_REASON_* keys."""
    if hold_reason_code in HOLD_CODE_MEMORY:
        return HOLD_REASON_MEMORY_LIMIT
    if hold_reason_code == HOLD_CODE_PERIODIC:
        return HOLD_REASON_WALLTIME
    return HOLD_REASON_OTHER


def classify_failure_event(htcondor, event_type: int) -> str:
    """Map an HTCondor JobEventType onto one of the FAILURE_* keys."""
    event_types = htcondor.JobEventType
    if event_type == event_types.SHADOW_EXCEPTION:
        return FAILURE_SHADOW_EXCEPTION
    if event_type == event_types.JOB_ABORTED:
        return FAILURE_JOB_ABORTED
    if event_type == event_types.CLUSTER_REMOVE:
        return FAILURE_CLUSTER_REMOVED
    if event_type == event_types.EXECUTABLE_ERROR:
        return FAILURE_EXECUTABLE_ERROR
    return FAILURE_UNKNOWN


class EventLogSummary(NamedTuple):
    job_running: bool
    job_complete: bool
    failure_event: int | None
    job_held: bool  # level: the job is held as of now, seeded from the prior cycle
    term_signal: int | None  # signal that killed the process (e.g. 9), None if normal exit
    hold_reason_code: int  # HoldReasonCode from JOB_HELD ClassAd, 0 if absent
    log_missing: bool = False  # True when the event log file does not exist
    job_released: bool = False  # True when a JOB_RELEASED event was seen this cycle
    job_held_event: bool = False  # edge: a JOB_HELD event was seen this cycle


class _EventState:
    """Mutable accumulator used while replaying a batch of event-log entries."""

    def __init__(self, running: bool, held: bool = False) -> None:
        self.job_running = running
        self.job_complete = False
        self.failure_event: int | None = None
        self.job_held = held
        self.term_signal: int | None = None
        self.hold_reason_code = 0
        self.job_released = False
        self.job_held_event = False

    def summary(self) -> EventLogSummary:
        return EventLogSummary(
            self.job_running,
            self.job_complete,
            self.failure_event,
            self.job_held,
            self.term_signal,
            self.hold_reason_code,
            job_released=self.job_released,
            job_held_event=self.job_held_event,
        )


def _apply_event(htcondor, state: _EventState, event) -> None:
    event_types = htcondor.JobEventType
    event_type = event.type
    if event_type == event_types.EXECUTE:
        state.job_running = True
        state.job_held = False
    elif event_type in (event_types.JOB_EVICTED, event_types.JOB_SUSPENDED):
        state.job_running = False
    elif event_type == event_types.JOB_UNSUSPENDED:
        state.job_running = True
    elif event_type == event_types.JOB_TERMINATED:
        state.job_complete = True
        if not event.get("TerminatedNormally", True):
            state.term_signal = int(event.get("TermSignal", 0)) or None
    elif event_type == event_types.JOB_HELD:
        state.job_running = False
        state.job_held = True
        state.job_held_event = True
        state.hold_reason_code = int(event.get("HoldReasonCode", 0))
    elif event_type == event_types.JOB_RELEASED:
        state.job_held = False
        state.job_running = False
        state.hold_reason_code = 0
        state.job_released = True
    elif event_type in (
        event_types.JOB_ABORTED,
        event_types.CLUSTER_REMOVE,
        event_types.SHADOW_EXCEPTION,
        event_types.EXECUTABLE_ERROR,
    ):
        state.failure_event = event_type


def summarize_event_log(
    htcondor, event_log, cluster_id: int, running: bool = False, held: bool = False
) -> EventLogSummary:
    """Replay the events appended to event_log since the last call.

    ``running`` and ``held`` seed the summary so that a cycle producing no new
    events reports the state the caller already believed the job to be in.
    Seeding ``held`` is what makes ``job_held`` a level signal: a job held once
    and never released emits a single JOB_HELD event, so without the seed it
    would appear un-held on every later cycle.
    """
    state = _EventState(running, held)
    for event in event_log.events(stop_after=0):
        if event.cluster != cluster_id or event.proc != 0:
            continue
        _apply_event(htcondor, state, event)
    return state.summary()


class HTCondorEventLogTracker:
    """Per-job event-log handle plus the counters driving failure escalation.

    Designed to be mixed into an application's job-state object (Galaxy's
    ``HTCondorJobState``, Pulsar's manager-side job state) so that both sides
    share the escalation bookkeeping as well as the parsing.
    """

    def __init__(self, user_log: str, clock=time.monotonic) -> None:
        self.user_log = user_log
        self._event_log: Any = None
        self.held_count = 0
        # Injectable so tests can drive escalation without sleeping.
        self.clock = clock
        self.status_error_since: float | None = None
        self.missing_log_since: float | None = None
        self.held_since: float | None = None
        self.held_reason_code = 0

    def note_status_error(self) -> float:
        """Record a failed status check, returning seconds since the first one."""
        now = self.clock()
        if self.status_error_since is None:
            self.status_error_since = now
        return now - self.status_error_since

    def clear_status_errors(self) -> None:
        self.status_error_since = None

    def note_missing_log(self) -> float:
        """Record an absent event log, returning seconds since it went missing."""
        now = self.clock()
        if self.missing_log_since is None:
            self.missing_log_since = now
        return now - self.missing_log_since

    def clear_missing_log(self) -> None:
        self.missing_log_since = None

    def note_held(self, hold_reason_code: int = 0) -> float:
        """Record that the job is held, returning seconds since it first was.

        The reason code is remembered from the JOB_HELD event that opened the
        hold.  Later cycles produce no new events, so the summary reports a
        reason code of 0 by then, yet the caller still needs to know which
        limit to name when the grace window expires.
        """
        now = self.clock()
        if self.held_since is None:
            self.held_since = now
        if hold_reason_code:
            self.held_reason_code = hold_reason_code
        return now - self.held_since

    def clear_held(self) -> None:
        self.held_since = None
        self.held_reason_code = 0

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

    def summarize(self, htcondor, cluster_id: int, running: bool = False, held: bool = False) -> EventLogSummary:
        """Summarize new event-log entries, reporting log_missing if absent."""
        if not os.path.exists(self.user_log):
            return EventLogSummary(running, False, None, held, None, 0, log_missing=True)
        return summarize_event_log(htcondor, self.event_log(htcondor), cluster_id, running, held)


class HTCondorClient:
    """Submits to and removes jobs from a schedd."""

    def submit(self, submit_description: str, collector: str | None, schedd_name: str | None) -> str:
        raise NotImplementedError()

    def remove(self, job_spec: int | str, collector: str | None, schedd_name: str | None) -> None:
        raise NotImplementedError()

    def shutdown(self) -> None:
        pass


class HTCondorInProcessClient(HTCondorClient):
    """Talks to the schedd directly, using the process-wide HTCondor config."""

    def __init__(self, htcondor, remove_reason: str = DEFAULT_REMOVE_REASON):
        self.htcondor = htcondor
        self.remove_reason = remove_reason
        self._schedd_cache: dict = {}
        self._schedd_lock = threading.Lock()

    def _schedd(self, collector: str | None, schedd_name: str | None):
        return locate_schedd(self.htcondor, self._schedd_cache, self._schedd_lock, collector, schedd_name)

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
                self.htcondor.JobAction.Remove, job_spec, reason=self.remove_reason
            )
        except Exception:
            self._evict_schedd(collector, schedd_name)
            raise


class HTCondorSubprocessClient(HTCondorClient):
    """Talks to a schedd through a helper subprocess with its own CONDOR_CONFIG.

    htcondor2 reads its configuration once per process, so a destination that
    overrides CONDOR_CONFIG cannot share the parent process with any other
    configuration.
    """

    def __init__(
        self,
        condor_config: str,
        helper_module: str = HTCONDOR_HELPER_MODULE,
        remove_reason: str = DEFAULT_REMOVE_REASON,
    ):
        self.condor_config = condor_config
        self.helper_module = helper_module
        self.remove_reason = remove_reason
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
                reason=self.remove_reason,
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

    def _terminate_process_locked(self, process: subprocess.Popen[str]) -> None:
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
        for path in os.environ.get("PYTHONPATH", "").split(os.pathsep):
            if path and path not in sys_paths:
                sys_paths.append(path)
        env["PYTHONPATH"] = os.pathsep.join(sys_paths)
        self._process = subprocess.Popen(
            [sys.executable, "-m", self.helper_module],
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

    def _start_stderr_drain(self, process: subprocess.Popen[str]) -> None:
        """Drain the helper's stderr into _stderr_lines and the application log.

        Runs as a daemon thread so HTCondor warnings (e.g. credential expiry)
        surface in the log rather than being silently discarded.
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

        drain_thread = threading.Thread(target=_drain, daemon=True, name="htcondor-helper-stderr")
        drain_thread.start()

    def _helper_failure_message_locked(self, message: str) -> str:
        # Stderr is consumed by the drain thread and buffered in _stderr_lines.
        recent = "\n".join(list(self._stderr_lines)[-10:]).strip()
        if recent:
            return f"{message}: {recent}"
        return message


class HTCondorClientCache:
    """Clients keyed by normalized CONDOR_CONFIG path.

    A ``None`` key means "use the configuration this process was started with"
    and is served in-process; every other key gets its own helper subprocess.
    """

    def __init__(
        self,
        htcondor,
        helper_module: str = HTCONDOR_HELPER_MODULE,
        remove_reason: str = DEFAULT_REMOVE_REASON,
    ) -> None:
        self.htcondor = htcondor
        self.helper_module = helper_module
        self.remove_reason = remove_reason
        self._clients: dict = {}
        self._lock = threading.Lock()

    def client_for_config(self, condor_config: str | None) -> HTCondorClient:
        condor_config = normalize_condor_config(condor_config)
        with self._lock:
            client = self._clients.get(condor_config)
            if client is None:
                if condor_config is None:
                    client = HTCondorInProcessClient(self.htcondor, remove_reason=self.remove_reason)
                else:
                    client = HTCondorSubprocessClient(
                        condor_config,
                        helper_module=self.helper_module,
                        remove_reason=self.remove_reason,
                    )
                self._clients[condor_config] = client
        return client

    def clients(self) -> list:
        """Snapshot of the currently cached clients."""
        with self._lock:
            return list(self._clients.values())

    def shutdown(self) -> None:
        with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()
        for client in clients:
            try:
                client.shutdown()
            except Exception:
                log.exception("Failed to shut down HTCondor client")

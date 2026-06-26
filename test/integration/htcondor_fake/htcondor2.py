"""Fake htcondor2 module for testing.

Mirrors the real htcondor2 Python API surface used by the Galaxy runner.
JobEventType integer values match the real htcondor2 library exactly so that
tests exercising event-log logic stay faithful to production behaviour.

When GALAXY_TEST_FAKE_HTCONDOR_AUTO_COMPLETE is set, Schedd.submit() writes a
dummy log file and pre-populates completion events so the Galaxy monitor thread
can finish the job without a real HTCondor installation.
"""

import enum
import json
import os
import re
import subprocess
import threading
import time
import uuid

_NEXT_CLUSTER_ID = 100
_NEXT_CLUSTER_ID_LOCK = threading.Lock()


def _current_config():
    condor_config = os.environ.get("CONDOR_CONFIG")
    if not condor_config:
        return None
    return os.path.realpath(condor_config)


def _record(kind, **payload):
    record_dir = os.environ.get("GALAXY_TEST_FAKE_HTCONDOR_RECORD_DIR")
    if not record_dir:
        return
    os.makedirs(record_dir, exist_ok=True)
    record = dict(
        kind=kind,
        pid=os.getpid(),
        config=_current_config(),
        **payload,
    )
    path = os.path.join(record_dir, f"{time.time_ns()}_{os.getpid()}_{uuid.uuid4().hex}.json")
    with open(path, "w") as handle:
        json.dump(record, handle)


def _next_cluster_id():
    global _NEXT_CLUSTER_ID
    with _NEXT_CLUSTER_ID_LOCK:
        cluster_id = _NEXT_CLUSTER_ID
        _NEXT_CLUSTER_ID += 1
    return cluster_id


def _parse_submit_field(submit_description: str, field: str) -> str | None:
    m = re.search(rf"^{re.escape(field)}\s*=\s*(.+)$", submit_description, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else None


def _create_job_log(submit_description: str) -> str | None:
    log_path = _parse_submit_field(submit_description, "log")
    if not log_path:
        return None
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w") as fh:
        fh.write("fake condor log\n")
    return log_path


def _mark_job_pending(submit_description: str, cluster_id: int) -> None:
    if log_path := _create_job_log(submit_description):
        JobEventLog.events_by_log[log_path] = [
            FakeJobEvent(cluster_id, 0, JobEventType.SUBMIT),
            FakeJobEvent(cluster_id, 0, JobEventType.EXECUTE),
        ]


def _auto_complete_job(submit_description: str, cluster_id: int) -> None:
    """Execute the job and inject completion events so the monitor can finish the job."""
    log_path = _create_job_log(submit_description)
    if not log_path:
        return
    executable = _parse_submit_field(submit_description, "executable")
    stdout_path = _parse_submit_field(submit_description, "output")
    stderr_path = _parse_submit_field(submit_description, "error")

    # Actually run the job so that output files are produced.
    if executable and os.path.isfile(executable):
        with (
            open(stdout_path, "w") if stdout_path else open(os.devnull, "w") as fout,
            open(stderr_path, "w") if stderr_path else open(os.devnull, "w") as ferr,
        ):
            subprocess.run(["/bin/bash", executable], stdout=fout, stderr=ferr)

    JobEventLog.events_by_log[log_path] = [
        FakeJobEvent(cluster_id, 0, JobEventType.SUBMIT),
        FakeJobEvent(cluster_id, 0, JobEventType.EXECUTE),
        FakeJobEvent(cluster_id, 0, JobEventType.JOB_TERMINATED),
    ]


class Submit:
    def __init__(self, description):
        self.description = description


class SubmitResult:
    def __init__(self, cluster_id):
        self._cluster_id = cluster_id

    def cluster(self):
        return self._cluster_id


# Values match real htcondor2 exactly (IntEnum, same integers).
class JobEventType(enum.IntEnum):
    SUBMIT = 0
    EXECUTE = 1
    EXECUTABLE_ERROR = 2
    CHECKPOINTED = 3
    JOB_EVICTED = 4
    JOB_TERMINATED = 5
    IMAGE_SIZE = 6
    SHADOW_EXCEPTION = 7
    GENERIC = 8
    JOB_ABORTED = 9
    JOB_SUSPENDED = 10
    JOB_UNSUSPENDED = 11
    JOB_HELD = 12
    JOB_RELEASED = 13
    CLUSTER_SUBMIT = 35
    CLUSTER_REMOVE = 36


class JobAction(enum.IntEnum):
    Hold = 1
    Release = 2
    Remove = 3
    RemoveX = 4
    Vacate = 5
    VacateFast = 6
    Suspend = 8
    Continue = 9


class DaemonType(enum.IntEnum):
    Schedd = 1


class FakeJobEvent:
    def __init__(self, cluster, proc, event_type, **classad_attrs):
        self.cluster = cluster
        self.proc = proc
        self.type = event_type
        self._classad = classad_attrs

    def get(self, key, default=None):
        return self._classad.get(key, default)


class Collector:
    def __init__(self, pool=None):
        self.pool = pool

    def locate(self, daemon_type, name=None):
        return dict(
            Name=name or "schedd@local",
            MyAddress="addr",
            CondorVersion="v1",
            Pool=self.pool,
        )

    def locateAll(self, daemon_type):
        return [self.locate(daemon_type)]


class JobEventLog:
    events_by_log: dict[str, list[FakeJobEvent]] = {}

    def __init__(self, filename):
        self.filename = filename

    @classmethod
    def set_events(cls, filename, events):
        cls.events_by_log[filename] = list(events)

    def events(self, stop_after=None):
        pending = self.events_by_log.pop(self.filename, [])
        yield from pending

    def close(self):
        pass


class Schedd:
    def __init__(self, location=None):
        self.location = location

    def submit(self, description, count=0, spool=False, itemdata=None, queue=None):
        cluster_id = _next_cluster_id()
        _record(
            "submit",
            collector=None if self.location is None else self.location.get("Pool"),
            schedd_name=None if self.location is None else self.location.get("Name"),
            submit_description=description.description,
            cluster_id=cluster_id,
        )
        if os.environ.get("GALAXY_TEST_FAKE_HTCONDOR_AUTO_COMPLETE"):
            _auto_complete_job(description.description, cluster_id)
        else:
            _mark_job_pending(description.description, cluster_id)
        return SubmitResult(cluster_id)

    def act(self, action, job_spec, reason=None):
        _record(
            "remove",
            collector=None if self.location is None else self.location.get("Pool"),
            schedd_name=None if self.location is None else self.location.get("Name"),
            action=action.name if hasattr(action, "name") else str(action),
            job_spec=job_spec,
            reason=reason,
        )
        return {}


def reload_config():
    return None

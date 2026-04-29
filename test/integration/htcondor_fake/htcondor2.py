import enum
import json
import os
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


class Submit:
    def __init__(self, description):
        self.description = description


class SubmitResult:
    def __init__(self, cluster_id):
        self._cluster_id = cluster_id

    def cluster(self):
        return self._cluster_id


class JobEventType(enum.IntEnum):
    SUBMIT = 0
    EXECUTE = 1
    IMAGE_SIZE = 2
    JOB_EVICTED = 3
    JOB_SUSPENDED = 4
    JOB_UNSUSPENDED = 5
    JOB_TERMINATED = 6
    JOB_ABORTED = 7
    JOB_HELD = 8
    CLUSTER_REMOVE = 9


class JobAction(enum.Enum):
    Remove = "Remove"


class DaemonType(enum.IntEnum):
    Schedd = 1


class FakeJobEvent:
    def __init__(self, cluster, proc, event_type):
        self.cluster = cluster
        self.proc = proc
        self.type = event_type


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
        events = self.events_by_log.get(self.filename, [])
        self.events_by_log[self.filename] = []
        yield from events


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
        return SubmitResult(cluster_id)

    def act(self, action, job_spec, reason=None):
        _record(
            "remove",
            collector=None if self.location is None else self.location.get("Pool"),
            schedd_name=None if self.location is None else self.location.get("Name"),
            action=action.value if hasattr(action, "value") else str(action),
            job_spec=job_spec,
            reason=reason,
        )
        return {}


def reload_config():
    return None

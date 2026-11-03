"""Tests for coordinating tool source store populates across processes."""

import os
import subprocess
import sys
import threading
import time
from datetime import timedelta
from typing import Any

import pytest

from galaxy.tools.source_store.composite import CompositeToolSourceStore
from galaxy.tools.source_store.coordination import populate_once
from galaxy.tools.source_store.interface import (
    PopulateLease,
    PopulateLeaseBusy,
    PopulateLeaseError,
)
from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore

FAST: dict[str, Any] = {"poll_interval": 0.02, "renew_interval": 0.05}


@pytest.fixture
def store(tmp_path):
    store = SqlAlchemyToolSourceStore(url=f"sqlite:///{tmp_path / 'store.sqlite'}")
    yield store
    store.dispose()


def _lease(store):
    lease = store.populate_lease()
    assert lease is not None
    return lease


def test_takes_over_the_lease_of_a_holder_that_died(store):
    lease = _lease(store)
    assert lease.try_acquire("dead process", ttl=timedelta(seconds=0.3))
    thread, calls, result = _populate_in_thread(lease)
    thread.join(10)
    assert result == [True]
    assert calls == [1]


def test_failed_populate_releases_the_lease_without_recording_it(store):
    lease = _lease(store)

    def fail():
        raise RuntimeError("populate failed")

    with pytest.raises(RuntimeError):
        populate_once(lease, lambda: True, fail, **FAST)
    # Free at once rather than after the TTL, and not recorded as populated,
    # so a waiter populates instead of reusing the failed result.
    assert lease.try_acquire("waiter", ttl=timedelta(minutes=1))
    assert lease.last_populated_at() is None


def test_holder_keeps_the_lease_past_its_ttl_while_populating(store):
    lease = _lease(store)
    ttl = timedelta(seconds=0.3)
    taken_over = []

    def slow_populate():
        time.sleep(0.8)
        taken_over.append(lease.try_acquire("other process", ttl))

    assert populate_once(lease, lambda: True, slow_populate, ttl=ttl, **FAST)
    assert taken_over == [False]


class _FlakyLease(PopulateLease):
    """Delegates to a real lease, failing the operations named in ``fail``."""

    def __init__(self, lease, fail_acquires=0, fail_release=False):
        self._lease = lease
        self._fail_acquires = fail_acquires
        self._fail_release = fail_release

    def last_populated_at(self):
        return self._lease.last_populated_at()

    def try_acquire(self, holder, ttl):
        if self._fail_acquires:
            self._fail_acquires -= 1
            raise PopulateLeaseBusy("database is locked")
        return self._lease.try_acquire(holder, ttl)

    def renew(self, holder, ttl):
        return self._lease.renew(holder, ttl)

    def release(self, holder, populated):
        if self._fail_release:
            raise PopulateLeaseError("disk I/O error")
        self._lease.release(holder, populated)


def _populate_in_thread(lease, **kwds):
    calls: list[int] = []
    result: list[bool] = []
    thread = threading.Thread(
        target=lambda: result.append(populate_once(lease, lambda: True, lambda: calls.append(1), **FAST, **kwds))
    )
    thread.start()
    return thread, calls, result


def test_uses_a_populate_another_process_completed_while_waiting(store):
    lease = _lease(store)
    assert lease.try_acquire("peer", ttl=timedelta(minutes=1))
    thread, calls, result = _populate_in_thread(lease)
    time.sleep(0.2)
    lease.release("peer", populated=True)
    thread.join(10)
    assert result == [False]
    assert calls == []


def test_repopulates_when_the_peer_result_is_unusable(store):
    lease = _lease(store)
    assert lease.try_acquire("peer", ttl=timedelta(minutes=1))
    thread, calls, result = _populate_in_thread(lease, peer_result_usable=lambda: False)
    time.sleep(0.2)
    lease.release("peer", populated=True)
    thread.join(10)
    assert result == [True]
    assert calls == [1]


def test_keeps_waiting_through_transient_database_errors(store):
    real_lease = _lease(store)
    assert real_lease.try_acquire("peer", ttl=timedelta(minutes=1))
    thread, calls, result = _populate_in_thread(_FlakyLease(real_lease, fail_acquires=3))
    time.sleep(0.2)
    assert calls == []
    real_lease.release("peer", populated=True)
    thread.join(10)
    assert result == [False]
    assert calls == []


def test_failed_release_does_not_fail_the_populate(store):
    calls = []
    lease = _FlakyLease(_lease(store), fail_release=True)
    assert populate_once(lease, lambda: True, lambda: calls.append(1), **FAST)
    assert calls == [1]


def test_populates_without_coordination_when_the_lease_table_is_missing(store):
    lease = _lease(store)
    with store._engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE tool_source_populate_lease")
    calls = []
    assert populate_once(lease, lambda: True, lambda: calls.append(1), **FAST)
    assert calls == [1]


def test_composite_store_uses_the_default_store_lease(tmp_path, store):
    published = SqlAlchemyToolSourceStore(url=f"sqlite:///{tmp_path / 'published.sqlite'}")
    published.dispose()
    read_only = SqlAlchemyToolSourceStore(url=f"sqlite:///{tmp_path / 'published.sqlite'}", read_only=True)
    composite = CompositeToolSourceStore(
        members=[("published", read_only), ("__default__", store)], default="__default__"
    )
    lease = composite.populate_lease()
    assert lease is not None
    assert lease.try_acquire("me", ttl=timedelta(minutes=1))
    assert not _lease(store).try_acquire("other", ttl=timedelta(minutes=1))


_POPULATE_ON_SIGNAL = """
import os, sys, time
import galaxy.tools.source_store.sqlalchemy as sqlalchemy_store
from galaxy.tools.source_store.coordination import populate_once

# Waiting for the populate must not depend on the SQLite busy timeout.
sqlalchemy_store.SQLITE_BUSY_TIMEOUT_SECONDS = 1
url, ready, go, populated_log, done = sys.argv[1:]
store = sqlalchemy_store.SqlAlchemyToolSourceStore(url=url)
open(ready, "w").close()
while not os.path.exists(go):
    time.sleep(0.001)

def populate():
    with open(populated_log, "a") as f:
        f.write(f"{os.getpid()}\\n")
    time.sleep(3)
    open(done, "w").close()

populate_once(store.populate_lease(), lambda: not os.path.exists(done), populate, poll_interval=0.05, renew_interval=0.5)
"""


def test_one_of_many_processes_populates_while_the_others_wait(tmp_path):
    url = f"sqlite:///{tmp_path / 'store.sqlite'}"
    go = tmp_path / "go"
    populated_log = tmp_path / "populated.log"
    ready_files = [tmp_path / f"ready-{i}" for i in range(6)]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                _POPULATE_ON_SIGNAL,
                url,
                str(ready),
                str(go),
                str(populated_log),
                str(tmp_path / "done"),
            ],
            env=env,
            stderr=subprocess.PIPE,
            text=True,
        )
        for ready in ready_files
    ]
    try:
        deadline = time.monotonic() + 120
        while not all(ready.exists() for ready in ready_files):
            assert all(p.poll() is None for p in processes), "a populate process exited before the start signal"
            assert time.monotonic() < deadline, "populate processes did not start"
            time.sleep(0.01)
        go.touch()
        errors = [p.communicate(timeout=120)[1] for p in processes]
    finally:
        for p in processes:
            p.kill()
    assert [p.returncode for p in processes] == [0] * len(processes), "\n".join(errors)
    assert len(populated_log.read_text().splitlines()) == 1

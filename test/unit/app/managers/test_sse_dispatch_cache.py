"""Tests for the TTL cache on ``SSEEventDispatcher._get_declare_queues``.

The cache exists because ``_send`` is on a hot path (1000+ events/s at target
load) and without it each dispatch fires a ``WorkerProcess`` DB query. The
underlying data only changes on a 60 s heartbeat cadence, so a 30 s TTL is safe.
"""

from concurrent.futures import (
    as_completed,
    ThreadPoolExecutor,
)
from typing import Any
from unittest.mock import MagicMock

import pytest

from galaxy.managers import sse_dispatch
from galaxy.managers.sse_dispatch import SSEEventDispatcher


@pytest.fixture
def fake_declare(monkeypatch):
    """Replace ``all_control_queues_for_declare`` with a call-counting fake.

    Returns a non-empty list by default so the cache stores a value — empty
    results are intentionally not cached (see ``test_empty_result_not_cached``).
    """
    calls: dict[str, Any] = {"count": 0, "returns": [MagicMock(name="queue")]}

    def _fake(application_stack, webapp_only=False):
        calls["count"] += 1
        # Sanity: the dispatcher must always ask for webapp-only queues.
        assert webapp_only is True
        return calls["returns"]

    monkeypatch.setattr(sse_dispatch, "all_control_queues_for_declare", _fake)
    return calls


class FakeClock:
    """Controllable time source passed to ``SSEEventDispatcher``.

    Lets tests advance the dispatcher's TTL cache deterministically without
    reaching into ``cachetools`` internals.
    """

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def dispatcher(monkeypatch, clock):
    """Build a dispatcher with a stub queue_worker and stub application_stack.

    ``ControlTask`` is swapped for a no-op so ``_send`` doesn't try to open a
    real AMQP connection.
    """
    queue_worker = MagicMock(name="queue_worker")
    application_stack = MagicMock(name="application_stack")

    fake_control_task = MagicMock()
    fake_control_task.return_value.send_task = MagicMock()
    monkeypatch.setattr(sse_dispatch, "ControlTask", fake_control_task)

    return SSEEventDispatcher(queue_worker=queue_worker, application_stack=application_stack, clock=clock)


def test_declare_queues_cached_within_ttl(dispatcher, fake_declare):
    """Repeated dispatches inside the TTL window only hit the DB once."""
    for _ in range(10):
        dispatcher.notify_broadcast("payload")
    assert fake_declare["count"] == 1


def test_declare_queues_refetched_after_ttl(dispatcher, fake_declare, clock):
    """Once the TTL expires, the next call refetches exactly once."""
    dispatcher.notify_broadcast("payload")
    assert fake_declare["count"] == 1

    # Advance the injected clock past the TTL so the cache sees the entry as
    # expired on the next read.
    clock.advance(dispatcher._DECLARE_QUEUES_TTL_SECONDS + 1)

    dispatcher.notify_broadcast("payload")
    assert fake_declare["count"] == 2

    # Further dispatches at the advanced time reuse the newly populated entry.
    dispatcher.notify_broadcast("payload")
    assert fake_declare["count"] == 2


def test_empty_result_not_cached(dispatcher, fake_declare):
    """An empty list must not be pinned in the cache for the full TTL.

    Empty results arise during startup (before ``DatabaseHeartbeat`` writes the
    row) and on swallowed DB errors. Caching them would silently drop every SSE
    event until the next TTL expiry.
    """
    fake_declare["returns"] = []
    dispatcher.notify_broadcast("payload")
    dispatcher.notify_broadcast("payload")
    assert fake_declare["count"] == 2

    # Once the upstream starts returning a non-empty result, caching resumes.
    fake_declare["returns"] = [MagicMock(name="queue")]
    dispatcher.notify_broadcast("payload")
    dispatcher.notify_broadcast("payload")
    assert fake_declare["count"] == 3


def test_declare_queues_thread_safe_single_query_under_load(dispatcher, fake_declare):
    """Concurrent ``_send`` from many threads still only triggers one DB query.

    With stampede protection (RLock around the miss) all 500 dispatches should
    collapse to a single ``all_control_queues_for_declare`` call inside one TTL
    window. The assertion is exact (== 1), not loose, because the lock
    serializes the miss.
    """
    iterations = 500

    def work():
        dispatcher.notify_broadcast("payload")

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(work) for _ in range(iterations)]
        for future in as_completed(futures):
            future.result()

    assert fake_declare["count"] == 1

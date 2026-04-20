"""Unit tests for :class:`galaxy.managers.sse_dispatch.SSEEventDispatcher` observability.

Focus is on the statsd instrumentation contract AND the effect of dispatch:
counters/timers fire on the happy path and the ``_queue_worker is None``
early-return, payloads reach the broker with the expected task+kwargs, and the
dispatcher is a silent no-op when ``statsd_client`` is ``None``.

These tests use lightweight fakes (``FakeStatsdClient``, ``FakeControlTask``)
that record state we can assert against — rather than ``MagicMock`` call-lists —
so a regression that silently drops dispatch or stops recording metrics fails
the test for the right reason.
"""

from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
    Optional,
)
from unittest.mock import MagicMock

import pytest

from galaxy.managers.sse_dispatch import SSEEventDispatcher


@dataclass
class FakeStatsdClient:
    """In-memory stand-in for ``VanillaGalaxyStatsdClient``.

    Records ``incr`` and ``timing`` calls as plain data so tests assert on
    observable state (counter totals, recorded timings) instead of mock
    call-lists.
    """

    counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = field(default_factory=dict)
    timings: list[tuple[str, float, tuple[tuple[str, str], ...]]] = field(default_factory=list)

    def incr(self, metric: str, tags: Optional[dict[str, str]] = None) -> None:
        key = (metric, tuple(sorted((tags or {}).items())))
        self.counters[key] = self.counters.get(key, 0) + 1

    def timing(self, metric: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        self.timings.append((metric, value, tuple(sorted((tags or {}).items()))))

    def counter(self, metric: str, tags: Optional[dict[str, str]] = None) -> int:
        return self.counters.get((metric, tuple(sorted((tags or {}).items()))), 0)


@dataclass
class RecordedTask:
    payload: dict[str, Any]
    routing_key: str
    expiration: Optional[int]
    declare_queues: Any


class FakeControlTask:
    """Stand-in for ``ControlTask`` that records dispatches instead of touching AMQP."""

    instances: list["FakeControlTask"] = []

    def __init__(self, queue_worker) -> None:
        self.queue_worker = queue_worker
        self.sent: list[RecordedTask] = []
        FakeControlTask.instances.append(self)

    def send_task(
        self,
        payload: dict[str, Any],
        routing_key: str,
        expiration: Optional[int] = None,
        declare_queues: Any = None,
        **_: Any,
    ) -> None:
        self.sent.append(
            RecordedTask(
                payload=payload,
                routing_key=routing_key,
                expiration=expiration,
                declare_queues=declare_queues,
            )
        )


class BoomControlTask:
    """``ControlTask`` fake whose ``send_task`` always raises — exercises the finally block."""

    def __init__(self, queue_worker) -> None:
        self.queue_worker = queue_worker

    def send_task(self, **kwargs) -> None:
        raise RuntimeError("broker down")


@pytest.fixture
def application_stack():
    return MagicMock(name="ApplicationStack")


@pytest.fixture
def queue_worker():
    return MagicMock(name="GalaxyQueueWorker")


@pytest.fixture
def statsd() -> FakeStatsdClient:
    return FakeStatsdClient()


@pytest.fixture(autouse=True)
def _reset_fake_control_task_instances():
    FakeControlTask.instances.clear()
    yield
    FakeControlTask.instances.clear()


@pytest.fixture
def fake_control_task(monkeypatch) -> type[FakeControlTask]:
    monkeypatch.setattr("galaxy.managers.sse_dispatch.ControlTask", FakeControlTask)
    monkeypatch.setattr(
        "galaxy.managers.sse_dispatch.all_control_queues_for_declare",
        lambda *args, **kwargs: [],
    )
    return FakeControlTask


def test_dispatcher_no_op_when_queue_worker_is_none_and_no_statsd(application_stack):
    """No statsd client set and no queue_worker → silent no-op, no AttributeError."""
    dispatcher = SSEEventDispatcher(
        queue_worker=None,
        application_stack=application_stack,
        statsd_client=None,
    )
    # Must not raise, must not attempt to declare queues.
    dispatcher.notify_users([1, 2], "hello")
    dispatcher.notify_broadcast("hi")
    dispatcher.history_update({"1": [42]})


def test_dispatcher_records_skipped_counter_when_queue_worker_is_none(application_stack, statsd):
    """Two dispatches with no queue_worker → two skipped_no_qw increments, no timings."""
    dispatcher = SSEEventDispatcher(
        queue_worker=None,
        application_stack=application_stack,
        statsd_client=statsd,
    )
    dispatcher.notify_users([1], "hello")
    dispatcher.notify_broadcast("world")

    assert statsd.counter("galaxy.sse.dispatch.skipped_no_qw") == 2
    # No latency timing — we never got as far as the broker call.
    assert statsd.timings == []


def test_dispatcher_enqueues_payload_and_records_metrics_on_send(
    application_stack, queue_worker, statsd, fake_control_task
):
    """Happy path: payload reaches the broker AND counter+timer are recorded."""
    dispatcher = SSEEventDispatcher(
        queue_worker=queue_worker,
        application_stack=application_stack,
        statsd_client=statsd,
    )
    dispatcher.notify_users([1, 2], "hello")

    # Exactly one ControlTask constructed, one send_task recorded with the right
    # payload — asserts the dispatch *effect*, not just that a mock was called.
    assert len(fake_control_task.instances) == 1
    sent = fake_control_task.instances[0].sent
    assert len(sent) == 1
    assert sent[0].payload["task"] == "notify_users"
    assert sent[0].payload["kwargs"]["user_ids"] == [1, 2]
    assert sent[0].payload["kwargs"]["payload"] == "hello"
    assert "event_id" in sent[0].payload["kwargs"]
    assert sent[0].routing_key == "control.*"
    assert sent[0].expiration == 10

    # Counter + timer both recorded with matching task tag.
    assert statsd.counter("galaxy.sse.dispatch.count", {"task": "notify_users"}) == 1
    assert len(statsd.timings) == 1
    metric, _value, tags = statsd.timings[0]
    assert metric == "galaxy.sse.dispatch.latency_ms"
    assert dict(tags) == {"task": "notify_users"}


def test_dispatcher_timer_still_fires_on_send_exception(monkeypatch, application_stack, queue_worker, statsd):
    """Timer lives in ``finally`` — broker errors don't mask the latency metric."""
    monkeypatch.setattr(
        "galaxy.managers.sse_dispatch.all_control_queues_for_declare",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr("galaxy.managers.sse_dispatch.ControlTask", BoomControlTask)

    dispatcher = SSEEventDispatcher(
        queue_worker=queue_worker,
        application_stack=application_stack,
        statsd_client=statsd,
    )
    with pytest.raises(RuntimeError):
        dispatcher.history_update({"7": [1]})

    assert statsd.counter("galaxy.sse.dispatch.count", {"task": "history_update"}) == 1
    assert len(statsd.timings) == 1
    metric, _value, tags = statsd.timings[0]
    assert metric == "galaxy.sse.dispatch.latency_ms"
    assert dict(tags) == {"task": "history_update"}


def test_dispatcher_no_statsd_means_no_instrumentation(application_stack, queue_worker, fake_control_task):
    """When ``statsd_client`` is ``None`` instrumentation is bypassed entirely.

    The dispatch still happens — we assert via the ControlTask fake — but there
    is nothing to observe on the (absent) statsd side.
    """
    dispatcher = SSEEventDispatcher(
        queue_worker=queue_worker,
        application_stack=application_stack,
        statsd_client=None,
    )
    dispatcher.notify_broadcast("hi")
    assert len(fake_control_task.instances) == 1
    assert len(fake_control_task.instances[0].sent) == 1
    assert fake_control_task.instances[0].sent[0].payload["task"] == "notify_broadcast"

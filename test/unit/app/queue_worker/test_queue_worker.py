import datetime
import time
from dataclasses import (
    dataclass,
    field,
)
from math import inf
from types import SimpleNamespace
from typing import Optional
from unittest.mock import MagicMock

import pytest

from galaxy.model.database_heartbeat import DatabaseHeartbeat
from galaxy.queue_worker import (
    GalaxyQueueWorker,
    send_control_task,
    send_local_control_task,
)
from galaxy.queues import connection_from_config
from galaxy.web_stack import application_stack_instance


@dataclass
class FakeStatsdClient:
    """In-memory statsd recorder — see docstring in ``test_sse_dispatch.py``."""

    counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = field(default_factory=dict)
    timings: list[tuple[str, float, tuple[tuple[str, str], ...]]] = field(default_factory=list)

    def incr(self, metric: str, tags: Optional[dict[str, str]] = None) -> None:
        key = (metric, tuple(sorted((tags or {}).items())))
        self.counters[key] = self.counters.get(key, 0) + 1

    def timing(self, metric: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        self.timings.append((metric, value, tuple(sorted((tags or {}).items()))))

    def counter(self, metric: str, tags: Optional[dict[str, str]] = None) -> int:
        return self.counters.get((metric, tuple(sorted((tags or {}).items()))), 0)

    def timings_for(self, metric: str) -> list[tuple[float, dict[str, str]]]:
        return [(v, dict(t)) for m, v, t in self.timings if m == metric]


def bar(app, **kwargs):
    app.some_var = "bar"
    app.tasks_executed.append("echo")
    return "bar"


control_message_to_task = {"echo": bar}


@pytest.fixture()
def queue_worker_factory(request, database_app):
    def app_factory():
        app = setup_queue_worker_test(database_app())
        request.addfinalizer(app.queue_worker.shutdown)
        request.addfinalizer(app.database_heartbeat.shutdown)
        return app

    return app_factory


def setup_queue_worker_test(app):
    app.some_var = "foo"
    app.tasks_executed = []
    server_name = f"{app.amqp_type}.{datetime.datetime.now()}"
    app.config.server_name = server_name
    app.config.server_names = [server_name]
    app.config.attach_to_pools = False
    app.amqp_internal_connection_obj = connection_from_config(app.config)
    app.application_stack = application_stack_instance(app=app)
    app.database_heartbeat = DatabaseHeartbeat(application_stack=app.application_stack, heartbeat_interval=10)
    app.database_heartbeat.start()
    time.sleep(0.2)
    app.queue_worker = GalaxyQueueWorker(app=app, task_mapping=control_message_to_task)
    app.queue_worker.bind_and_start()
    time.sleep(0.5)
    return app


def test_send_control_task(queue_worker_factory):
    app = queue_worker_factory()
    send_control_task(app=app, task="echo")
    wait_for_var(app, "some_var", "bar")
    assert len(app.tasks_executed) == 1


def test_send_control_task_to_many_listeners(queue_worker_factory):
    app1 = queue_worker_factory()
    app2 = queue_worker_factory()
    app3 = queue_worker_factory()
    app4 = queue_worker_factory()
    app5 = queue_worker_factory()
    send_control_task(app=app1, task="echo")
    for app in [app1, app2, app3, app4, app5]:
        wait_for_var(app, "some_var", "bar")
        assert len(app.tasks_executed) == 1


def test_send_control_task_get_result(queue_worker_factory):
    app = queue_worker_factory()
    response = send_control_task(app=app, task="echo", get_response=True)
    assert response == "bar"
    assert app.some_var == "bar"
    assert len(app.tasks_executed) == 1


def test_send_local_control_task(queue_worker_factory):
    app = queue_worker_factory()
    send_local_control_task(app=app, task="echo")
    wait_for_var(app, "some_var", "bar")
    assert len(app.tasks_executed) == 1


def test_send_local_control_task_with_past_message(queue_worker_factory):
    app = queue_worker_factory()
    app.queue_worker.epoch = inf
    response = send_local_control_task(app=app, task="echo", get_response=True)
    assert len(app.tasks_executed) == 0
    assert response == "NO_OP"


def test_send_local_control_task_with_non_target_listeners(queue_worker_factory):
    app1 = queue_worker_factory()
    app2 = queue_worker_factory()
    assert app2.some_var == "foo"
    send_local_control_task(app=app1, task="echo")
    wait_for_var(app1, "some_var", "bar")
    assert app2.some_var == "foo"
    assert len(app1.tasks_executed) == 1
    assert len(app2.tasks_executed) == 0


def test_send_control_task_noop_self(queue_worker_factory):
    app = queue_worker_factory()
    assert app.some_var == "foo"
    response = send_control_task(app=app, task="echo", noop_self=True, get_response=True)
    assert response == "NO_OP"
    assert app.some_var == "foo"
    assert len(app.tasks_executed) == 0


def wait_for_var(obj, var, value, tries=10, sleep=0.25):
    while getattr(obj, var) != value and tries >= 0:
        tries -= 1
        time.sleep(sleep)
    assert getattr(obj, var) == value


# ---------------------------------------------------------------------------
# process_task observability tests
#
# These don't need a real broker or DB — we just instantiate GalaxyQueueWorker
# via ``__new__`` and drive ``process_task`` directly with fake ``body`` /
# ``message`` objects.  The statsd client is pulled through
# ``app.execution_timer_factory.galaxy_statsd_client``.
# ---------------------------------------------------------------------------


def _make_fake_worker(task_fn, statsd_client):
    worker = GalaxyQueueWorker.__new__(GalaxyQueueWorker)
    worker.app = SimpleNamespace(
        config=SimpleNamespace(server_name="test.server"),
        execution_timer_factory=SimpleNamespace(galaxy_statsd_client=statsd_client),
    )
    worker.task_mapping = {"echo": task_fn}
    worker.epoch = 0
    # ``producer`` is a read-only property on the mixin; we avoid the publisher
    # path entirely by leaving ``reply_to`` out of the fake message properties.
    return worker


def _fake_message():
    message = MagicMock()
    message.headers = {"epoch": inf}  # always greater than worker.epoch
    message.properties = {}  # no reply_to — skip publisher path
    return message


def test_process_task_emits_counter_and_ok_timer():
    statsd = FakeStatsdClient()
    calls: list[dict] = []

    def handler(app, **kwargs):
        calls.append(kwargs)
        return "done"

    worker = _make_fake_worker(handler, statsd)
    worker.process_task({"task": "echo", "kwargs": {"x": 1}}, _fake_message())

    # Handler actually ran — if the worker silently dropped the task, this list
    # would be empty and the test would fail loudly.
    assert calls == [{"x": 1}]
    assert statsd.counter("galaxy.control_queue.task.count", {"task": "echo"}) == 1
    assert len(statsd.timings_for("galaxy.control_queue.task.latency_ms")) == 1
    _value, tags = statsd.timings_for("galaxy.control_queue.task.latency_ms")[0]
    assert tags == {"task": "echo", "outcome": "ok"}


def test_process_task_emits_error_timer_on_handler_exception():
    statsd = FakeStatsdClient()
    invocations: list[bool] = []

    def boom(app, **kwargs):
        invocations.append(True)
        raise RuntimeError("handler failed")

    worker = _make_fake_worker(boom, statsd)
    # process_task swallows handler exceptions (logged, not raised).
    worker.process_task({"task": "echo", "kwargs": {}}, _fake_message())

    # Handler was actually invoked before raising.
    assert invocations == [True]
    assert statsd.counter("galaxy.control_queue.task.count", {"task": "echo"}) == 1
    assert len(statsd.timings_for("galaxy.control_queue.task.latency_ms")) == 1
    _value, tags = statsd.timings_for("galaxy.control_queue.task.latency_ms")[0]
    assert tags == {"task": "echo", "outcome": "error"}


def test_process_task_no_statsd_is_silent_no_op():
    calls: list[dict] = []

    def handler(app, **kwargs):
        calls.append(kwargs)
        return "done"

    worker = _make_fake_worker(handler, statsd_client=None)
    worker.process_task({"task": "echo", "kwargs": {"x": 2}}, _fake_message())
    # Handler ran — the test guards both "no exception" AND "task not silently dropped".
    assert calls == [{"x": 2}]

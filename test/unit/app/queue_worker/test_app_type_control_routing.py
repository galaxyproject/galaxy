"""Verify webapp isolation and broadcast delivery through Kombu's memory transport."""

import uuid

import pytest
from kombu import Connection
from kombu.transport import (
    memory,
    virtual,
)

from galaxy.queues import (
    ALL_CONTROL,
    control_queue,
    galaxy_exchange,
    WEBAPP_APP_TYPE,
    WEBAPP_CONTROL_ROUTING_KEY,
)


@pytest.fixture(autouse=True)
def clean_broker_state():
    # The memory transport keeps broker state on the class, so bindings and
    # queues survive connection teardown and leak between tests.
    memory.Transport.global_state = virtual.BrokerState()
    memory.Channel.queues = {}
    yield
    memory.Transport.global_state = virtual.BrokerState()
    memory.Channel.queues = {}


@pytest.fixture
def broker():
    with Connection("memory://") as connection:
        yield connection


def _bind(connection, app_type):
    name = f"control.{app_type or 'handler'}.{uuid.uuid4().hex[:8]}@h"
    queue = control_queue(name, app_type=app_type)
    queue(connection.default_channel).declare()
    return queue


def _publish(connection, routing_key, declare):
    connection.Producer(connection.default_channel).publish(
        {"task": "history_update", "kwargs": {}},
        exchange=galaxy_exchange,
        routing_key=routing_key,
        declare=declare,
    )


def _received(connection, queue):
    return queue(connection.default_channel).get() is not None


def test_webapp_addressed_task_skips_job_handler(broker):
    webapp = _bind(broker, WEBAPP_APP_TYPE)
    handler = _bind(broker, None)

    _publish(broker, WEBAPP_CONTROL_ROUTING_KEY, declare=[webapp])

    assert _received(broker, webapp)
    assert not _received(broker, handler)


def test_webapp_addressed_task_skips_job_handler_even_when_its_queue_is_declared(broker):
    webapp = _bind(broker, WEBAPP_APP_TYPE)
    handler = _bind(broker, None)

    _publish(broker, WEBAPP_CONTROL_ROUTING_KEY, declare=[webapp, handler])

    assert _received(broker, webapp)
    assert not _received(broker, handler)


def test_broadcast_control_task_still_reaches_every_process(broker):
    webapp = _bind(broker, WEBAPP_APP_TYPE)
    handler = _bind(broker, None)

    _publish(broker, ALL_CONTROL, declare=[webapp, handler])

    assert _received(broker, webapp)
    assert _received(broker, handler)


def test_broadcast_control_task_delivered_once_to_a_webapp(broker):
    webapp = _bind(broker, WEBAPP_APP_TYPE)

    _publish(broker, ALL_CONTROL, declare=[webapp])

    assert _received(broker, webapp)
    assert not _received(broker, webapp)


def test_webapp_queue_binds_broadcast_and_web_control():
    keys = {b.routing_key for b in control_queue("control.web.1@h", app_type=WEBAPP_APP_TYPE).bindings}

    assert keys == {ALL_CONTROL, WEBAPP_CONTROL_ROUTING_KEY}


def test_handler_queue_binds_broadcast_only():
    keys = {b.routing_key for b in control_queue("control.handler.1@h").bindings}

    assert keys == {ALL_CONTROL}

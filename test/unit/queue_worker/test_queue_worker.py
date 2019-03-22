import contextlib
import logging
import time

import pytest


from galaxy.queue_worker import (
    GalaxyQueueWorker,
    send_control_task,
    send_local_control_task,
)
from galaxy.queues import connection_from_config

log = logging.getLogger(__name__)


def bar(app, **kwargs):
    app.some_var = 'bar'
    return 'bar'


control_message_to_task = {'echo': bar}


@pytest.fixture()
def queue_worker_app(database_app):
    with setup_queue_worker_test(database_app) as queue_worker_app:
        yield queue_worker_app


@contextlib.contextmanager
def setup_queue_worker_test(app):
    app.config.server_name = 'test_queue_worker'
    app.config.server_names = ['test_queue_worker']
    app.config.amqp_internal_connection = "sqlalchemy+" + app.config.database_connection
    app.amqp_internal_connection_obj = connection_from_config(app.config)
    app.control_worker = GalaxyQueueWorker(app=app, task_mapping=control_message_to_task)
    app.control_worker.bind_and_start()
    time.sleep(0.5)
    try:
        yield app
    finally:
        app.control_worker.shutdown()


def test_send_control_task(queue_worker_app):
    queue_worker_app.some_var = 'foo'
    send_control_task(app=queue_worker_app, task='echo')
    wait_for_var(queue_worker_app, 'some_var', 'bar')


def test_send_control_task_get_result(queue_worker_app):
    queue_worker_app.some_var = 'foo'
    response = send_control_task(app=queue_worker_app, task='echo', get_response=True)
    assert response == 'bar'
    assert queue_worker_app.some_var == 'bar'


def test_send_control_task_noop_self(queue_worker_app):
    queue_worker_app.some_var = 'foo'
    response = send_control_task(app=queue_worker_app, task='echo', noop_self=True, get_response=True)
    assert response == 'NO_OP'
    assert queue_worker_app.some_var == 'foo'


def test_send_local_control_task(queue_worker_app):
    queue_worker_app.some_var = 'foo'
    send_local_control_task(app=queue_worker_app, task='echo')
    wait_for_var(queue_worker_app, 'some_var', 'bar')


def wait_for_var(obj, var, value, tries=10, sleep=0.25):
    while getattr(obj, var) != value and tries >= 0:
        tries -= 1
        time.sleep(sleep)
    assert getattr(obj, var) == value

import contextlib
import time

import pytest


from galaxy.queue_worker import (
    GalaxyQueueWorker,
    send_control_task,
)
from galaxy.queues import connection_from_config


def bar(app, **kwargs):
    app.some_var = 'bar'


control_message_to_task = {'echo': bar}


@pytest.fixture()
def queue_worker_app(database_app):
    with setup_queue_worker_test(database_app) as queue_worker_app:
        yield queue_worker_app


@contextlib.contextmanager
def setup_queue_worker_test(app):
    app.config.server_name = 'test_queue_worker'
    app.config.server_names = ['test_server_name', 'test_queue_worker']
    app.config.amqp_internal_connection = "sqlalchemy+" + app.config.database_connection
    app.amqp_internal_connection_obj = connection_from_config(app.config)
    queue_worker = GalaxyQueueWorker(app=app, task_mapping=control_message_to_task)
    queue_worker.bind_and_start()
    time.sleep(0.5)
    try:
        yield app
    finally:
        queue_worker.shutdown()


def test_queue_worker_echo(queue_worker_app):
    queue_worker_app.some_var = 'foo'
    send_control_task(app=queue_worker_app, task='echo')
    wait_for_var(queue_worker_app, 'some_var', 'bar')


def wait_for_var(obj, var, value, tries=10, sleep=0.25):
    while getattr(obj, var) != value and tries >= 0:
        tries -= 1
        time.sleep(sleep)
    assert getattr(obj, var) == value

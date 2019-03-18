import os
import tempfile
import time

import pytest

from galaxy.queue_worker import (
    GalaxyQueueWorker,
    send_control_task,
)
from galaxy.queues import connection_from_config
from ..tools_support import UsesApp


def foo(app, **kwargs):
    app.some_var = 'bar'


control_message_to_task = {'echo': foo}


@pytest.fixture
def sqlite_database_path():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    os.remove(path)


@pytest.fixture
def simple_app(sqlite_database_path):
    test = UsesApp()
    test.setup_app()
    test.app.config.server_name = 'test_queue_worker'
    test.app.config.server_names = ['test_server_name', 'test_queue_worker']
    test.app.config.amqp_internal_connection = 'sqlalchemy+sqlite:////%s' % sqlite_database_path
    test.app.amqp_internal_connection_obj = connection_from_config(test.app.config)
    test.queue_worker = GalaxyQueueWorker(app=test.app, task_mapping=control_message_to_task)
    test.queue_worker.bind_and_start()
    yield test.app
    test.queue_worker.shutdown()


def test_queue_worker_echo(simple_app):
    simple_app.some_var = 'foo'
    send_control_task(app=simple_app, task='echo')
    wait_for_var(simple_app, 'some_var', 'bar')


def wait_for_var(obj, var, value, tries=10, sleep=0.25):
    while getattr(obj, var) != value and tries >= 0:
        tries -= 1
        time.sleep(sleep)
    assert getattr(obj, var) == value

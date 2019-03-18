import contextlib
import os
import sys
import tempfile
import time

import pytest

from galaxy.queue_worker import (
    GalaxyQueueWorker,
    send_control_task,
)
from galaxy.queues import connection_from_config
from galaxy.util import which
from ..tools_support import UsesApp


def foo(app, **kwargs):
    app.some_var = 'bar'


control_message_to_task = {'echo': foo}


@pytest.fixture
def sqlite_connection():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield 'sqlalchemy+sqlite:////%s' % path
    os.remove(path)


@pytest.fixture
def simple_app(sqlite_connection):
    with create_test(sqlite_connection) as test:
        yield test.app


@pytest.fixture
def postgres_app(postgresql_db):
    connection = "sqlalchemy+" + str(postgresql_db.engine.url)
    if postgresql_db.has_table('kombu_message'):
        raise Exception("postgresql table has kombu_message table, this shouldn't happen during tests.")
    with create_test(connection) as test:
        time.sleep(0.5)
        # Wait for kombu table setup
        yield test.app


@contextlib.contextmanager
def create_test(amqp_connection):
    test = UsesApp()
    test.setup_app()
    test.app.config.server_name = 'test_queue_worker'
    test.app.config.server_names = ['test_server_name', 'test_queue_worker']
    test.app.config.amqp_internal_connection = amqp_connection
    test.app.amqp_internal_connection_obj = connection_from_config(test.app.config)
    test.queue_worker = GalaxyQueueWorker(app=test.app, task_mapping=control_message_to_task)
    test.queue_worker.bind_and_start()
    try:
        yield test
    finally:
        test.queue_worker.shutdown()


@pytest.mark.skipif(sys.version_info[0] < 3,
                    reason="postgresql_db fixture requires python 3 or higher")
@pytest.mark.skipif(not which('initdb'), reason='reason postgresql initdb not on PATH')
def test_queue_worker_echo_postgresql(postgres_app):
    postgres_app.some_var = 'foo'
    send_control_task(app=postgres_app, task='echo')
    wait_for_var(postgres_app, 'some_var', 'bar')


def test_queue_worker_echo(simple_app):
    simple_app.some_var = 'foo'
    send_control_task(app=simple_app, task='echo')
    wait_for_var(simple_app, 'some_var', 'bar')


def wait_for_var(obj, var, value, tries=10, sleep=0.25):
    while getattr(obj, var) != value and tries >= 0:
        tries -= 1
        time.sleep(sleep)
    assert getattr(obj, var) == value

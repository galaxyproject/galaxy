import contextlib
import time

import pytest

from galaxy.queue_worker import (
    GalaxyQueueWorker,
    send_control_task,
    send_local_control_task,
)
from galaxy.queues import connection_from_config
from galaxy.web.stack import application_stack_instance
from galaxy.web.stack.database_heartbeat import DatabaseHeartbeat


def bar(app, **kwargs):
    app.some_var = 'bar'
    return 'bar'


control_message_to_task = {'echo': bar}


@pytest.fixture()
def queue_worker_factory(database_app):

    def app_factory(server_name):
        with setup_queue_worker_test(database_app(), server_name) as queue_worker_app:
            return queue_worker_app

    return app_factory


@contextlib.contextmanager
def setup_queue_worker_test(app, server_name):
    app.some_var = 'foo'
    app.config.server_name = server_name
    app.config.server_names = [server_name]
    app.config.attach_to_pools = False
    app.config.amqp_internal_connection = "sqlalchemy+" + app.config.database_connection
    app.amqp_internal_connection_obj = connection_from_config(app.config)
    app.application_stack = application_stack_instance(app=app)
    app.database_heartbeat = DatabaseHeartbeat(sa_session=app.model.context, application_stack=app.application_stack, heartbeat_interval=10)
    app.database_heartbeat.start()
    time.sleep(0.2)
    app.control_worker = GalaxyQueueWorker(app=app, task_mapping=control_message_to_task)
    app.control_worker.bind_and_start()
    time.sleep(0.2)
    try:
        yield app
    finally:
        app.control_worker.shutdown()
        app.database_heartbeat.shutdown()


def test_send_control_task(queue_worker_factory):
    app = queue_worker_factory('test_server')
    send_control_task(app=app, task='echo')
    wait_for_var(app, 'some_var', 'bar')


def test_send_control_task_to_many_listeners(queue_worker_factory):
    app1 = queue_worker_factory('test_server1')
    app2 = queue_worker_factory('test_server2')
    send_control_task(app=app1, task='echo')
    for app in [app1, app2]:
        wait_for_var(app, 'some_var', 'bar')


def test_send_control_task_get_result(queue_worker_factory):
    app = queue_worker_factory('test_server')
    response = send_control_task(app=app, task='echo', get_response=True)
    assert response == 'bar'
    assert app.some_var == 'bar'


def test_send_local_control_task_with_non_target_listeners(queue_worker_factory):
    app1 = queue_worker_factory('test_server1')
    app2 = queue_worker_factory('test_server2')
    assert app2.some_var == 'foo'
    send_local_control_task(app=app1, task='echo')
    wait_for_var(app1, 'some_var', 'bar')
    assert app2.some_var == 'foo'


def test_send_control_task_noop_self(queue_worker_factory):
    app = queue_worker_factory('test_server')
    assert app.some_var == 'foo'
    response = send_control_task(app=app, task='echo', noop_self=True, get_response=True)
    assert response == 'NO_OP'
    assert app.some_var == 'foo'


def test_send_local_control_task(queue_worker_factory):
    app = queue_worker_factory('test_server')
    send_local_control_task(app=app, task='echo')
    wait_for_var(app, 'some_var', 'bar')


def wait_for_var(obj, var, value, tries=10, sleep=0.25):
    while getattr(obj, var) != value and tries >= 0:
        tries -= 1
        time.sleep(sleep)
    assert getattr(obj, var) == value

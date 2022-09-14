import datetime
import time
from math import inf

import pytest

from galaxy.model.database_heartbeat import DatabaseHeartbeat
from galaxy.queue_worker import (
    GalaxyQueueWorker,
    send_control_task,
    send_local_control_task,
)
from galaxy.queues import connection_from_config
from galaxy.web_stack import application_stack_instance


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

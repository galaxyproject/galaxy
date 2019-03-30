import contextlib
import time

import pytest

from galaxy.web.stack import application_stack_instance
from galaxy.web.stack.database_heartbeat import DatabaseHeartbeat


@pytest.fixture
def heartbeat_app(database_app):
    with setup_heartbeat_app(database_app()) as heartbeat_app:
        yield heartbeat_app


@contextlib.contextmanager
def setup_heartbeat_app(app):
    app.config.server_name = 'test_heartbeat'
    app.config.attach_to_pools = False
    app.application_stack = application_stack_instance(app=app)
    app.database_heartbeat = DatabaseHeartbeat(application_stack=app.application_stack, heartbeat_interval=0.1)
    yield app
    app.database_heartbeat.shutdown()


def test_database_heartbeat(heartbeat_app):
    active_processes = heartbeat_app.database_heartbeat.get_active_processes()
    assert len(active_processes) == 0
    heartbeat_app.database_heartbeat.start()
    # thread needs to start
    time.sleep(0.5)
    active_processes = heartbeat_app.database_heartbeat.get_active_processes()
    assert len(active_processes) == 1
    process = active_processes[0]
    update_time = process.update_time
    time.sleep(0.2)
    heartbeat_app.model.context.refresh(process)
    next_update_time = process.update_time
    assert update_time < next_update_time
    heartbeat_app.database_heartbeat.shutdown()
    time.sleep(0.5)
    assert len(heartbeat_app.database_heartbeat.get_active_processes(last_seen_seconds=5)) == 1
    assert len(heartbeat_app.database_heartbeat.get_active_processes(last_seen_seconds=0.4)) == 0

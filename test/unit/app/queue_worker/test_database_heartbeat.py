import contextlib
import time

import pytest

import galaxy.model.database_heartbeat as heartbeat
import galaxy.web_stack as stack


@pytest.fixture
def heartbeat_app(database_app):
    class QueueWorker:
        def send_control_task(self, *args, **kwargs):
            return

    with setup_heartbeat_app(database_app()) as heartbeat_app:
        heartbeat_app.queue_worker = QueueWorker()
        yield heartbeat_app


@contextlib.contextmanager
def setup_heartbeat_app(app):
    app.config.server_name = "test_heartbeat"
    app.config.attach_to_pools = False
    app.application_stack = stack.application_stack_instance(app=app)
    app.database_heartbeat = heartbeat.DatabaseHeartbeat(
        application_stack=app.application_stack, heartbeat_interval=0.1
    )
    yield app
    app.database_heartbeat.shutdown()


def test_database_heartbeat(heartbeat_app):
    active_processes = heartbeat_app.database_heartbeat.get_active_processes()
    assert len(active_processes) == 0
    heartbeat_app.database_heartbeat.start()

    def one_active_process():
        active_processes = heartbeat_app.database_heartbeat.get_active_processes()
        assert len(active_processes) == 1
        process = active_processes[0]
        return process

    # thread needs to start
    process = wait_for_assertion(one_active_process)
    update_time = process.update_time

    def process_updated():
        heartbeat_app.model.context.refresh(process)
        next_update_time = process.update_time
        assert update_time < next_update_time

    wait_for_assertion(process_updated)

    heartbeat_app.database_heartbeat.shutdown()
    # shutdown() remove the worker process from the database, so no active process will be found
    assert len(heartbeat_app.database_heartbeat.get_active_processes(last_seen_seconds=5)) == 0


def wait_for_assertion(assert_f):
    assertion_error = None
    for _ in range(10):
        try:
            v = assert_f()
            return v
        except AssertionError as e:
            assertion_error = e
        time.sleep(0.2)

    if assertion_error:
        raise assertion_error

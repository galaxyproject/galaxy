"""Tests for ``all_control_queues_for_declare`` process filtering.

The standalone SSE monitor registers a liveness ``WorkerProcess`` row (for the
audit-monitor election) but runs no control consumer, so it must be excluded
from the general control-queue routing table — otherwise producers declare and
feed a queue nothing drains. Webapps and job handlers (``app_type`` NULL) must
still be routed to. The ``webapp_only`` path stays webapp-only for SSE events.

Uses the real sqlite ``database_app`` fixture and inserts real ``WorkerProcess``
rows so the SQL filter is exercised, not mocked.
"""

import galaxy.web_stack as stack
from galaxy.model import WorkerProcess
from galaxy.model.database_heartbeat import (
    SSE_MONITOR,
    WEBAPP,
)
from galaxy.queues import all_control_queues_for_declare
from galaxy.util import now


def _make_app(database_app):
    app = database_app()
    app.config.attach_to_pools = False
    app.application_stack = stack.application_stack_instance(app=app)
    return app


def _insert_processes(app):
    with app.model.new_session() as session, session.begin():
        session.add_all(
            [
                WorkerProcess(server_name="web.1", hostname="h", app_type=WEBAPP, update_time=now()),
                WorkerProcess(server_name="handler.1", hostname="h", app_type=None, update_time=now()),
                WorkerProcess(server_name="sse_monitor.h.7", hostname="h", app_type=SSE_MONITOR, update_time=now()),
            ]
        )


def _queue_names(queues):
    return {q.name for q in queues}


def test_general_declare_excludes_sse_monitor(database_app):
    app = _make_app(database_app)
    _insert_processes(app)

    names = _queue_names(all_control_queues_for_declare(app.application_stack))

    # Webapp and the NULL-app_type job handler are routed to; the SSE monitor is not.
    assert names == {"control.web.1@h", "control.handler.1@h"}


def test_webapp_only_declare_returns_only_webapps(database_app):
    app = _make_app(database_app)
    _insert_processes(app)

    names = _queue_names(all_control_queues_for_declare(app.application_stack, webapp_only=True))

    assert names == {"control.web.1@h"}

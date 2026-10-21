"""

All message queues used by Galaxy

"""

import datetime
import logging
import socket

from kombu import (
    binding,
    Connection,
    Exchange,
    Queue,
)
from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.orm import Session

from galaxy.model import WorkerProcess
from galaxy.util import now
from galaxy.web_stack import ApplicationStack

log = logging.getLogger(__name__)

ALL_CONTROL = "control.*"
# Keep webapp routing outside control.* so broadcast bindings cannot match it.
WEBAPP_CONTROL_ROUTING_KEY = "web.control"
galaxy_exchange = Exchange("galaxy_core_exchange", type="topic")

DEFAULT_ACTIVE_PROCESS_WINDOW_SECONDS = 120
# Matches WorkerProcess.app_type set by DatabaseHeartbeat for webapp processes.
WEBAPP_APP_TYPE = "webapp"
# Matches WorkerProcess.app_type for the standalone SSE monitor. It registers a
# liveness heartbeat for the audit-monitor election but runs no control
# consumer, so it must be kept out of the control-queue routing table.
SSE_MONITOR_APP_TYPE = "sse_monitor"


def control_queues_for_session(session: Session, webapp_only: bool = False) -> list[Queue]:
    """Build the per-process control-queue declare list from a model session.

    Split out of :func:`all_control_queues_for_declare` so callers that have a
    bare session but no ``ApplicationStack`` — notably the standalone
    tool-source populator CLI — can build the same routing table.
    """
    stmt = select(WorkerProcess).where(
        WorkerProcess.update_time > now() - datetime.timedelta(seconds=DEFAULT_ACTIVE_PROCESS_WINDOW_SECONDS)
    )
    if webapp_only:
        stmt = stmt.where(WorkerProcess.app_type == WEBAPP_APP_TYPE)
    else:
        # ``!=`` alone would drop NULL app_type rows (job handlers); keep them.
        stmt = stmt.where(or_(WorkerProcess.app_type != SSE_MONITOR_APP_TYPE, WorkerProcess.app_type.is_(None)))
    processes = session.scalars(stmt).all()
    return [control_queue(f"control.{p.server_name}@{p.hostname}", app_type=p.app_type) for p in processes]


def all_control_queues_for_declare(application_stack: ApplicationStack, webapp_only: bool = False) -> list[Queue]:
    """Declare active consumer bindings for virtual transports' in-memory routing.

    Query WorkerProcess directly so Celery producers need no heartbeat thread.
    Exclude the SSE monitor, which has no consumer; optionally limit to webapps.
    Delivery is determined by routing keys, not this declaration list.
    """
    app = application_stack.app
    try:
        with app.model.new_session() as session:
            return control_queues_for_session(session, webapp_only=webapp_only)
    except Exception:
        log.debug("Failed to look up active processes for control-queue declare", exc_info=True)
        return []


def control_queue(queue_name: str, app_type: str | None = None) -> Queue:
    """Bind a process queue to broadcasts and, for webapps, web control tasks."""
    bindings = [binding(galaxy_exchange, routing_key=ALL_CONTROL)]
    if app_type == WEBAPP_APP_TYPE:
        bindings.append(binding(galaxy_exchange, routing_key=WEBAPP_CONTROL_ROUTING_KEY))
    return Queue(queue_name, bindings=bindings)


def control_queues_from_config(config, app_type: str | None = None):
    """
    Returns a Queue instance with the correct name and routing key for this
    galaxy process's config
    """
    hostname = socket.gethostname()
    process_name = f"{config.server_name}@{hostname}"
    exchange_queue = control_queue(f"control.{process_name}", app_type=app_type)
    non_exchange_queue = Queue(f"control.{process_name}", routing_key=f"control.{process_name}")
    return exchange_queue, non_exchange_queue


def connection_from_config(config) -> Connection | None:
    if config.amqp_internal_connection:
        return Connection(config.amqp_internal_connection)
    else:
        return None

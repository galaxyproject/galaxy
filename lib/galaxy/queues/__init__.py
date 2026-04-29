"""

All message queues used by Galaxy

"""

import datetime
import logging
import socket
from typing import (
    Optional,
    TYPE_CHECKING,
)

from kombu import (
    Connection,
    Exchange,
    Queue,
)
from sqlalchemy import select

from galaxy.model import WorkerProcess
from galaxy.model.orm.now import now

if TYPE_CHECKING:
    from galaxy.web_stack import ApplicationStack

log = logging.getLogger(__name__)

ALL_CONTROL = "control.*"
galaxy_exchange = Exchange("galaxy_core_exchange", type="topic")

DEFAULT_ACTIVE_PROCESS_WINDOW_SECONDS = 120
# Matches WorkerProcess.app_type set by DatabaseHeartbeat for webapp processes.
WEBAPP_APP_TYPE = "webapp"


def all_control_queues_for_declare(application_stack: "ApplicationStack", webapp_only: bool = False) -> list[Queue]:
    """
    For in-memory routing (used by sqlalchemy-based transports), we need to be able to
    build the entire routing table in producers.

    Queries ``WorkerProcess`` directly rather than going through
    ``DatabaseHeartbeat`` so this works from Celery workers too — they have a
    ``model`` but no heartbeat thread. Without this, a notification created in
    a Celery task publishes a ``notify_users`` control task with an empty
    ``declare`` list, so on the sqlalchemy+sqlite kombu transport the message
    never lands in a web worker's queue.

    When ``webapp_only`` is True, only returns queues for processes that have
    registered themselves with ``app_type='webapp'``. This is what the SSE
    dispatcher wants: job handlers and workflow schedulers have no browser
    connections, so routing SSE events to them is wasted work.
    """
    app = application_stack.app
    try:
        stmt = select(WorkerProcess).where(
            WorkerProcess.update_time > now() - datetime.timedelta(seconds=DEFAULT_ACTIVE_PROCESS_WINDOW_SECONDS)
        )
        if webapp_only:
            stmt = stmt.where(WorkerProcess.app_type == WEBAPP_APP_TYPE)
        with app.model.new_session() as session:
            processes = session.scalars(stmt).all()
    except Exception:
        log.debug("Failed to look up active processes for control-queue declare", exc_info=True)
        return []
    return [Queue(f"control.{p.server_name}@{p.hostname}", galaxy_exchange, routing_key="control.*") for p in processes]


def control_queues_from_config(config):
    """
    Returns a Queue instance with the correct name and routing key for this
    galaxy process's config
    """
    hostname = socket.gethostname()
    process_name = f"{config.server_name}@{hostname}"
    exchange_queue = Queue(f"control.{process_name}", galaxy_exchange, routing_key="control.*")
    non_exchange_queue = Queue(f"control.{process_name}", routing_key=f"control.{process_name}")
    return exchange_queue, non_exchange_queue


def connection_from_config(config) -> Optional[Connection]:
    if config.amqp_internal_connection:
        return Connection(config.amqp_internal_connection)
    else:
        return None

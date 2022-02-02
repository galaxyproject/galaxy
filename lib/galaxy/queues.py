"""

All message queues used by Galaxy

"""
import socket
from typing import Optional

from kombu import (
    Connection,
    Exchange,
    Queue,
)

ALL_CONTROL = "control.*"
galaxy_exchange = Exchange("galaxy_core_exchange", type="topic")


def all_control_queues_for_declare(application_stack):
    """
    For in-memory routing (used by sqlalchemy-based transports), we need to be able to
    build the entire routing table in producers.
    """
    # Get all active processes and construct queues for each process
    process_names = (
        "{p.server_name}@{p.hostname}".format(p=p)
        for p in application_stack.app.database_heartbeat.get_active_processes()
    )
    return [Queue(f"control.{server_name}", galaxy_exchange, routing_key="control.*") for server_name in process_names]


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

"""

All message queues used by Galaxy

"""

from kombu import (
    Connection,
    Exchange,
    Queue
)

ALL_CONTROL = "control.*"
galaxy_exchange = Exchange('galaxy_core_exchange', type='topic')


def all_control_queues_for_declare(config, application_stack):
    """
    For in-memory routing (used by sqlalchemy-based transports), we need to be able to
    build the entire routing table in producers.
    """
    # Get all active processes and construct queues for each process
    if application_stack and application_stack.app:
        server_names = (p.server_name for p in application_stack.app.database_heartbeat.get_active_processes())
    else:
        server_names = config.server_names
    return [Queue("control.%s" % server_name, galaxy_exchange, routing_key='control.*') for server_name in server_names]


def control_queue_from_config(config):
    """
    Returns a Queue instance with the correct name and routing key for this
    galaxy process's config
    """
    return Queue("control.%s" % config.server_name,
                 galaxy_exchange,
                 routing_key='control.%s' % config.server_name)


def connection_from_config(config):
    if config.amqp_internal_connection:
        return Connection(config.amqp_internal_connection)
    else:
        return None

"""

All message queues used by Galaxy

"""

from galaxy.util.postfork import process_is_uwsgi

from kombu import Exchange, Queue, Connection

ALL_CONTROL = "control.*"
galaxy_exchange = Exchange('galaxy_core_exchange', type='topic')


def all_control_queues_for_declare(config):
    """
    For in-memory routing (used by sqlalchemy-based transports), we need to be able to
    build the entire routing table in producers.

    Refactor later to actually persist this somewhere instead of building it repeatedly.
    """
    possible_uwsgi_queues = []
    if process_is_uwsgi:
        import uwsgi
        possible_uwsgi_queues = [Queue("control.%s.%s" % (config.server_name.split('.')[0], wkr['id']), galaxy_exchange, routing_key='control') for wkr in uwsgi.workers()]
    return possible_uwsgi_queues + [Queue('control.%s' % q, galaxy_exchange, routing_key='control') for q in config.server_names]


def control_queue_from_config(config):
    """
    Returns a Queue instance with the correct name and routing key for this
    galaxy process's config
    """
    return Queue("control.%s" % config.server_name, galaxy_exchange, routing_key='control')


def connection_from_config(config):
    if config.amqp_internal_connection:
        return Connection(config.amqp_internal_connection)
    else:
        return None

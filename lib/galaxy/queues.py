"""

All message queues used by Galaxy

"""

import sys

from galaxy import eggs

eggs.require('anyjson')
if sys.version_info < (2, 7, 0):
    # Kombu requires importlib and ordereddict to function in Python 2.6.
    eggs.require('importlib')
    eggs.require('ordereddict')
eggs.require('kombu')
from kombu import Exchange, Queue

ALL_CONTROL = "control.*"
galaxy_exchange = Exchange('galaxy_core_exchange', type='topic')


def all_control_queues_for_declare(config):
    """
    For in-memory routing (used by sqlalchemy-based transports), we need to be able to
    build the entire routing table in producers.

    Refactor later to actually persist this somewhere instead of building it repeatedly.
    """
    return [Queue('control.%s' % q, galaxy_exchange, routing_key='control') for
            q in config.server_names]


def control_queue_from_config(config):
    """
    Returns a Queue instance with the correct name and routing key for this
    galaxy process's config
    """
    return Queue("control.%s" % config.server_name, galaxy_exchange,
                 routing_key='control')

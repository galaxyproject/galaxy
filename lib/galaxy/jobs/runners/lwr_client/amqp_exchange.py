try:
    import kombu
    from kombu import pools
except ImportError:
    kombu = None

import socket
import logging
from time import sleep
log = logging.getLogger(__name__)


KOMBU_UNAVAILABLE = "Attempting to bind to AMQP message queue, but kombu dependency unavailable"

DEFAULT_EXCHANGE_NAME = "lwr"
DEFAULT_EXCHANGE_TYPE = "direct"
# Set timeout to periodically give up looking and check if polling should end.
DEFAULT_TIMEOUT = 0.2


class LwrExchange(object):
    """ Utility for publishing and consuming structured LWR queues using kombu.
    This is shared between the server and client - an exchange should be setup
    for each manager (or in the case of the client, each manager one wished to
    communicate with.)

    Each LWR manager is defined solely by name in the scheme, so only one LWR
    should target each AMQP endpoint or care should be taken that unique
    manager names are used across LWR servers targetting same AMQP endpoint -
    and in particular only one such LWR should define an default manager with
    name _default_.
    """

    def __init__(self, url, manager_name, connect_ssl=None, timeout=DEFAULT_TIMEOUT):
        """
        """
        if not kombu:
            raise Exception(KOMBU_UNAVAILABLE)
        self.__url = url
        self.__manager_name = manager_name
        self.__connect_ssl = connect_ssl
        self.__exchange = kombu.Exchange(DEFAULT_EXCHANGE_NAME, DEFAULT_EXCHANGE_TYPE)
        self.__timeout = timeout

    @property
    def url(self):
        return self.__url

    def consume(self, queue_name, callback, check=True, connection_kwargs={}):
        queue = self.__queue(queue_name)
        log.debug("Consuming queue '%s'", queue)
        while check:
            try:
                with self.connection(self.__url, ssl=self.__connect_ssl, **connection_kwargs) as connection:
                    with kombu.Consumer(connection, queues=[queue], callbacks=[callback], accept=['json']):
                        while check and connection.connected:
                            try:
                                connection.drain_events(timeout=self.__timeout)
                            except socket.timeout:
                                pass
            except socket.error, exc:
                log.warning('Got socket.error, will retry: %s', exc)
                sleep(1)

    def publish(self, name, payload):
        with self.connection(self.__url, ssl=self.__connect_ssl) as connection:
            with pools.producers[connection].acquire() as producer:
                key = self.__queue_name(name)
                producer.publish(
                    payload,
                    serializer='json',
                    exchange=self.__exchange,
                    declare=[self.__exchange],
                    routing_key=key,
                )

    def connection(self, connection_string, **kwargs):
        return kombu.Connection(connection_string, **kwargs)

    def __queue(self, name):
        queue_name = self.__queue_name(name)
        queue = kombu.Queue(queue_name, self.__exchange, routing_key=queue_name)
        return queue

    def __queue_name(self, name):
        key_prefix = self.__key_prefix()
        queue_name = '%s_%s' % (key_prefix, name)
        return queue_name

    def __key_prefix(self):
        if self.__manager_name == "_default_":
            key_prefix = "lwr_"
        else:
            key_prefix = "lwr_%s_" % self.__manager_name
        return key_prefix

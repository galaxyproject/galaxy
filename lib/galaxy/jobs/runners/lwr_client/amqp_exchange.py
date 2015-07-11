try:
    import kombu
    from kombu import pools
except ImportError:
    kombu = None

import socket
import logging
import threading
from time import sleep
log = logging.getLogger(__name__)


KOMBU_UNAVAILABLE = "Attempting to bind to AMQP message queue, but kombu dependency unavailable"

DEFAULT_EXCHANGE_NAME = "lwr"
DEFAULT_EXCHANGE_TYPE = "direct"
# Set timeout to periodically give up looking and check if polling should end.
DEFAULT_TIMEOUT = 0.2
DEFAULT_HEARTBEAT = 580

DEFAULT_RECONNECT_CONSUMER_WAIT = 1
DEFAULT_HEARTBEAT_WAIT = 1


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

    def __init__(
        self,
        url,
        manager_name,
        connect_ssl=None,
        timeout=DEFAULT_TIMEOUT,
        publish_kwds={},
    ):
        """
        """
        if not kombu:
            raise Exception(KOMBU_UNAVAILABLE)
        self.__url = url
        self.__manager_name = manager_name
        self.__connect_ssl = connect_ssl
        self.__exchange = kombu.Exchange(DEFAULT_EXCHANGE_NAME, DEFAULT_EXCHANGE_TYPE)
        self.__timeout = timeout
        # Be sure to log message publishing failures.
        if publish_kwds.get("retry", False):
            if "retry_policy" not in publish_kwds:
                publish_kwds["retry_policy"] = {}
            if "errback" not in publish_kwds["retry_policy"]:
                publish_kwds["retry_policy"]["errback"] = self.__publish_errback
        self.__publish_kwds = publish_kwds

    @property
    def url(self):
        return self.__url

    def consume(self, queue_name, callback, check=True, connection_kwargs={}):
        queue = self.__queue(queue_name)
        log.debug("Consuming queue '%s'", queue)
        while check:
            heartbeat_thread = None
            try:
                with self.connection(self.__url, heartbeat=DEFAULT_HEARTBEAT, **connection_kwargs) as connection:
                    with kombu.Consumer(connection, queues=[queue], callbacks=[callback], accept=['json']):
                        heartbeat_thread = self.__start_heartbeat(queue_name, connection)
                        while check and connection.connected:
                            try:
                                connection.drain_events(timeout=self.__timeout)
                            except socket.timeout:
                                pass
            except (IOError, socket.error), exc:
                # In testing, errno is None
                log.warning('Got %s, will retry: %s', exc.__class__.__name__, exc)
                if heartbeat_thread:
                    heartbeat_thread.join()
                sleep(DEFAULT_RECONNECT_CONSUMER_WAIT)

    def heartbeat(self, connection):
        log.debug('AMQP heartbeat thread alive')
        while connection.connected:
            connection.heartbeat_check()
            sleep(DEFAULT_HEARTBEAT_WAIT)
        log.debug('AMQP heartbeat thread exiting')

    def publish(self, name, payload):
        with self.connection(self.__url) as connection:
            with pools.producers[connection].acquire() as producer:
                key = self.__queue_name(name)
                producer.publish(
                    payload,
                    serializer='json',
                    exchange=self.__exchange,
                    declare=[self.__exchange],
                    routing_key=key,
                    **self.__publish_kwds
                )

    def __publish_errback(self, exc, interval):
        log.error("Connection error while publishing: %r", exc, exc_info=1)
        log.info("Retrying in %s seconds", interval)

    def connection(self, connection_string, **kwargs):
        if "ssl" not in kwargs:
            kwargs["ssl"] = self.__connect_ssl
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

    def __start_heartbeat(self, queue_name, connection):
        thread_name = "consume-heartbeat-%s" % (self.__queue_name(queue_name))
        thread = threading.Thread(name=thread_name, target=self.heartbeat, args=(connection,))
        thread.start()
        return thread

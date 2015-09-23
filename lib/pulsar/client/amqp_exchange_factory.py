from .amqp_exchange import PulsarExchange
from .util import filter_destination_params, MessageQueueUUIDStore


def get_exchange(url, manager_name, params):
    connect_ssl = parse_amqp_connect_ssl_params(params)
    exchange_kwds = dict(
        manager_name=manager_name,
        connect_ssl=connect_ssl,
        publish_kwds=parse_amqp_publish_kwds(params)
    )
    if params.get('amqp_acknowledge', False):
        exchange_kwds.update(parse_ack_kwds(params, manager_name))
    timeout = params.get('amqp_consumer_timeout', False)
    if timeout is not False:
        exchange_kwds['timeout'] = timeout
    exchange = PulsarExchange(url, **exchange_kwds)
    return exchange


def parse_amqp_connect_ssl_params(params):
    ssl_params = filter_destination_params(params, "amqp_connect_ssl_")
    if not ssl_params:
        return

    ssl = __import__('ssl')
    if 'cert_reqs' in ssl_params:
        value = ssl_params['cert_reqs']
        ssl_params['cert_reqs'] = getattr(ssl, value.upper())
    return ssl_params


def parse_amqp_publish_kwds(params):
    all_publish_params = filter_destination_params(params, "amqp_publish_")
    retry_policy_params = {}
    for key in all_publish_params.keys():
        if key.startswith("retry_"):
            value = all_publish_params[key]
            retry_policy_params[key[len("retry_"):]] = value
            del all_publish_params[key]
    if retry_policy_params:
        all_publish_params["retry_policy"] = retry_policy_params
    return all_publish_params


def parse_ack_kwds(params, manager_name):
    ack_params = {}
    persistence_directory = params.get('persistence_directory', None)
    if persistence_directory:
        subdirs = ['amqp_ack-%s' % manager_name]
        ack_params['publish_uuid_store'] = MessageQueueUUIDStore(persistence_directory, subdirs=subdirs + ['publish'])
        ack_params['consume_uuid_store'] = MessageQueueUUIDStore(persistence_directory, subdirs=subdirs + ['consume'])
    republish_time = params.get('amqp_ack_republish_time', None)
    if republish_time:
        ack_params['republish_time'] = int(republish_time)
    return ack_params

"""Return various facts for string formatting.
"""
import socket
from collections import MutableMapping

from six import string_types


class Facts(MutableMapping):
    """A dict-like object that evaluates values at access time."""

    def __init__(self, config=None, **kwargs):
        config = config or {}
        self.__dict__ = {}
        self.__set_defaults(config)
        self.__set_config(config)
        self.__dict__.update(dict(**kwargs))

    def __set_defaults(self, config):
        # config here may be a Galaxy config object, or it may just be a dict
        defaults = {
            'server_name': lambda: config.get('base_server_name', 'main'),
            'server_id': None,
            'instance_id': None,
            'pool_name': None,
            'fqdn': lambda: socket.getfqdn(),
            'hostname': lambda: socket.gethostname().split('.', 1)[0],
        }
        self.__dict__.update(defaults)

    def __set_config(self, config):
        if config is not None:
            for name in dir(config):
                if not name.startswith('_') and isinstance(getattr(config, name), string_types):
                    self.__dict__['config_' + name] = lambda name=name: getattr(config, name)

    def __getitem__(self, key):
        item = self.__dict__.__getitem__(key)
        if callable(item):
            return item()
        else:
            return item

    # Other methods pass through to the corresponding dict methods

    def __setitem__(self, key, value):
        return self.__dict__.__setitem__(key, value)

    def __delitem__(self, key):
        return self.__dict__.__delitem__(key)

    def __iter__(self):
        return self.__dict__.__iter__()

    def __len__(self):
        return self.__dict__.__len__()

    def __str__(self):
        return self.__dict__.__str__()

    def __repr__(self):
        return self.__dict__.__repr__()


def get_facts(config=None, **kwargs):
    return Facts(config=config, **kwargs)

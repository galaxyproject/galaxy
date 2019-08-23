import os
from collections import OrderedDict

import yaml


OPTION_DEFAULTS = {
    "type": "str",
    "unknown_option": False,
    "default": None,
    "desc": None,
}


def ordered_load(stream):
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    OrderedLoader.add_constructor('!include', OrderedLoader.include)

    return yaml.load(stream, OrderedLoader)


class OrderedLoader(yaml.Loader):
    # This class was pulled out of ordered_load() for the sake of
    # mocking __init__ in a unit test.
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(OrderedLoader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename, 'r') as f:
            return yaml.load(f, OrderedLoader)


def ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            list(data.items()))
    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)

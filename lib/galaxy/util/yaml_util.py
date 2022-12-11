import logging
import os
from collections import OrderedDict

import yaml
from yaml.constructor import ConstructorError

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader  # type: ignore[misc, assignment]


log = logging.getLogger(__name__)


class OrderedLoader(SafeLoader):
    # This class was pulled out of ordered_load() for the sake of
    # mocking __init__ in a unit test.
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super().__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename) as f:
            return yaml.load(f, OrderedLoader)


def ordered_load(stream, merge_duplicate_keys=False):
    """
    Parse the first YAML document in a stream and produce the corresponding
    Python object.

    If merge_duplicate_keys is True, merge the values of duplicate mapping keys
    into a list, as the uWSGI "dumb" YAML parser would do.
    Otherwise, following YAML 1.2 specification which says that "each key is
    unique in the association", raise a ConstructionError exception.
    """

    def construct_mapping(loader, node, deep=False):
        loader.flatten_mapping(node)
        mapping = {}
        merged_duplicate = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            value = loader.construct_object(value_node, deep=deep)
            if key in mapping:
                if not merge_duplicate_keys:
                    raise ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        f"found duplicated key ({key})",
                        key_node.start_mark,
                    )
                log.debug("Merging values for duplicate key '%s' into a list", key)
                if merged_duplicate.get(key):
                    mapping[key].append(value)
                else:
                    mapping[key] = [mapping[key], value]
                    merged_duplicate[key] = True
            else:
                mapping[key] = value
        return mapping

    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    OrderedLoader.add_constructor("!include", OrderedLoader.include)

    return yaml.load(stream, OrderedLoader)


def ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, list(data.items()))

    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)

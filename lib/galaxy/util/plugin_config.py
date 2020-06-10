import collections

try:
    import yaml
except ImportError:
    yaml = None

from galaxy.util import parse_xml
from galaxy.util.submodules import import_submodules


PluginConfigSource = collections.namedtuple('PluginConfigSource', ['type', 'source'])


def plugins_dict(module, plugin_type_identifier):
    """ Walk through all classes in submodules of module and find ones labelled
    with specified plugin_type_identifier and throw in a dictionary to allow
    constructions from plugins by these types later on.
    """
    plugin_dict = {}

    for plugin_module in import_submodules(module, ordered=True):
        for clazz in __plugin_classes_in_module(plugin_module):
            plugin_type = getattr(clazz, plugin_type_identifier, None)
            if plugin_type:
                plugin_dict[plugin_type] = clazz

    return plugin_dict


def load_plugins(plugins_dict, plugin_source, extra_kwds=None, plugin_type_keys=('type',)):
    if extra_kwds is None:
        extra_kwds = {}
    if plugin_source.type == "xml":
        return __load_plugins_from_element(plugins_dict, plugin_source.source, extra_kwds)
    else:
        return __load_plugins_from_dicts(plugins_dict, plugin_source.source, extra_kwds, plugin_type_keys=plugin_type_keys)


def __plugin_classes_in_module(plugin_module):
    for clazz in getattr(plugin_module, "__all__", []):
        try:
            clazz = getattr(plugin_module, clazz)
        except TypeError:
            clazz = clazz
        yield clazz


def __load_plugins_from_element(plugins_dict, plugins_element, extra_kwds):
    plugins = []

    for plugin_element in plugins_element:
        plugin_type = plugin_element.tag
        plugin_kwds = dict(plugin_element.items())
        plugin_kwds.update(extra_kwds)
        try:
            plugin_klazz = plugins_dict[plugin_type]
        except KeyError:
            template = "Failed to find plugin of type [%s] in available plugin types %s"
            message = template % (plugin_type, str(plugins_dict.keys()))
            raise Exception(message)

        plugin = plugin_klazz(**plugin_kwds)
        plugins.append(plugin)

    return plugins


def __load_plugins_from_dicts(plugins_dict, configs, extra_kwds, plugin_type_keys):
    plugins = []

    for config in configs:
        plugin_type = None
        for plugin_type_key in plugin_type_keys:
            if plugin_type_key in config:
                plugin_type = config[plugin_type_key]
                break
        assert plugin_type is not None, "Could not determine plugin type for [%s]" % config
        plugin_kwds = config
        plugin_kwds.update(extra_kwds)
        plugin = plugins_dict[plugin_type](**plugin_kwds)
        plugins.append(plugin)

    return plugins


def plugin_source_from_path(path):
    if path.endswith(".yaml") or path.endswith(".yml") or path.endswith(".yaml.sample") or path.endswith(".yml.sample"):
        return PluginConfigSource('dict', __read_yaml(path))
    else:
        return PluginConfigSource('xml', parse_xml(path, remove_comments=True).getroot())


def plugin_source_from_dict(as_dict):
    return PluginConfigSource('dict', as_dict)


def __read_yaml(path):
    if yaml is None:
        raise ImportError("Attempting to read YAML configuration file - but PyYAML dependency unavailable.")

    with open(path, "rb") as f:
        return yaml.safe_load(f)

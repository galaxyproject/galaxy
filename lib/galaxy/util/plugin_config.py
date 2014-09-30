from xml.etree import ElementTree

try:
    from galaxy import eggs
    eggs.require('PyYAML')
except Exception:
    # If not in Galaxy, ignore this.
    pass
try:
    import yaml
except ImportError:
    yaml = None

from galaxy.util.submodules import submodules


def plugins_dict(module, plugin_type_identifier):
    """ Walk through all classes in submodules of module and find ones labelled
    with specified plugin_type_identifier and throw in a dictionary to allow
    constructions from plugins by these types later on.
    """
    plugin_dict = {}

    for plugin_module in submodules( module ):
        # FIXME: this is not how one is suppose to use __all__ why did you do
        # this past John?
        for clazz in plugin_module.__all__:
            plugin_type = getattr( clazz, plugin_type_identifier, None )
            if plugin_type:
                plugin_dict[ plugin_type ] = clazz

    return plugin_dict


def load_plugins(plugins_dict, plugin_source, extra_kwds={}):
    source_type, source = plugin_source
    if source_type == "xml":
        return __load_plugins_from_element(plugins_dict, source, extra_kwds)
    else:
        return __load_plugins_from_dicts(plugins_dict, source, extra_kwds)


def __load_plugins_from_element(plugins_dict, plugins_element, extra_kwds):
    plugins = []

    for plugin_element in plugins_element.getchildren():
        plugin_type = plugin_element.tag
        plugin_kwds = dict( plugin_element.items() )
        plugin_kwds.update( extra_kwds )
        plugin = plugins_dict[ plugin_type ]( **plugin_kwds )
        plugins.append( plugin )

    return plugins


def __load_plugins_from_dicts(plugins_dict, configs, extra_kwds):
    plugins = []

    for config in configs:
        plugin_type = config[ "type" ]
        plugin_kwds = config
        plugin_kwds.update( extra_kwds )
        plugin = plugins_dict[ plugin_type ]( **plugin_kwds )
        plugins.append( plugin )

    return plugins


def plugin_source_from_path(path):
    if path.endswith(".yaml") or path.endswith(".yml"):
        return ('dict', __read_yaml(path))
    else:
        return ('xml', ElementTree.parse( path ).getroot())


def __read_yaml(path):
    if yaml is None:
        raise ImportError("Attempting to read YAML configuration file - but PyYAML dependency unavailable.")

    with open(path, "rb") as f:
        return yaml.load(f)

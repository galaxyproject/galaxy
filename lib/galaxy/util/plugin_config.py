from pathlib import Path
from types import ModuleType
from typing import (
    Any,
    cast,
    Dict,
    Generator,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Type,
    Union,
)

import yaml

from galaxy.util import parse_xml
from galaxy.util.submodules import import_submodules

PathT = Union[str, Path]
PluginDictConfigT = Dict[str, Any]
PluginConfigsT = Union[PluginDictConfigT, List[PluginDictConfigT]]


class PluginConfigSource(NamedTuple):
    type: str
    source: Any


def plugins_dict(module: ModuleType, plugin_type_identifier: str) -> Dict[str, Type]:
    """Walk through all classes in submodules of module and find ones labelled
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


def load_plugins(
    plugins_dict: Dict[str, Type],
    plugin_source: PluginConfigSource,
    extra_kwds: Optional[Dict[str, Any]] = None,
    plugin_type_keys: Iterable[str] = ("type",),
    dict_to_list_key: Optional[str] = None,
) -> List[Any]:
    if extra_kwds is None:
        extra_kwds = {}
    if plugin_source.type == "xml":
        return __load_plugins_from_element(plugins_dict, plugin_source.source, extra_kwds)
    else:
        return __load_plugins_from_dicts(
            plugins_dict,
            plugin_source.source,
            extra_kwds,
            plugin_type_keys=plugin_type_keys,
            dict_to_list_key=dict_to_list_key,
        )


def __plugin_classes_in_module(plugin_module: ModuleType) -> Generator[Type, None, None]:
    for clazz in getattr(plugin_module, "__all__", []):
        try:
            clazz = getattr(plugin_module, clazz)
        except TypeError:
            clazz = clazz
        yield clazz


def __load_plugins_from_element(
    plugins_dict: Dict[str, Type], plugins_element, extra_kwds: Dict[str, Any]
) -> List[Any]:
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


def __load_plugins_from_dicts(
    plugins_dict: Dict[str, Type],
    configs: PluginConfigsT,
    extra_kwds: Dict[str, Any],
    plugin_type_keys: Iterable[str],
    dict_to_list_key: Optional[str],
) -> List[Any]:
    plugins = []

    configs_as_list: List[PluginDictConfigT]
    if isinstance(configs, dict) and dict_to_list_key is not None:
        configs_as_list = []
        for key, value in configs.items():
            config = value.copy()
            config[dict_to_list_key] = key
            configs_as_list.append(config)
    else:
        configs_as_list = cast(List[PluginDictConfigT], configs)

    for config in configs_as_list:
        plugin_type = None
        for plugin_type_key in plugin_type_keys:
            if plugin_type_key in config:
                plugin_type = config[plugin_type_key]
                break
        assert plugin_type is not None, f"Could not determine plugin type for [{config}]"
        plugin_kwds = config
        if extra_kwds:
            plugin_kwds = plugin_kwds.copy()
            plugin_kwds.update(extra_kwds)
        plugin = plugins_dict[plugin_type](**plugin_kwds)
        plugins.append(plugin)

    return plugins


def plugin_source_from_path(path: PathT) -> PluginConfigSource:
    filename = str(path)
    if (
        filename.endswith(".yaml")
        or filename.endswith(".yml")
        or filename.endswith(".yaml.sample")
        or filename.endswith(".yml.sample")
    ):
        return PluginConfigSource("dict", __read_yaml(path))
    else:
        return PluginConfigSource("xml", parse_xml(path, remove_comments=True).getroot())


def plugin_source_from_dict(as_dict: PluginConfigsT) -> PluginConfigSource:
    return PluginConfigSource("dict", as_dict)


def __read_yaml(path: PathT):
    if yaml is None:
        raise ImportError("Attempting to read YAML configuration file - but PyYAML dependency unavailable.")

    with open(path, "rb") as f:
        return yaml.safe_load(f)

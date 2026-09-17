from collections.abc import (
    Generator,
    Iterable,
)
from types import ModuleType
from typing import (
    Any,
    cast,
    NamedTuple,
    Protocol,
    TypeVar,
)

import yaml

from galaxy.util import parse_xml
from galaxy.util.path import StrPath
from galaxy.util.submodules import import_submodules

PluginDictConfigT = dict[str, Any]
PluginConfigsT = PluginDictConfigT | list[PluginDictConfigT]


class ConfigurablePlugin(Protocol):
    @classmethod
    def build_template_config(cls, **kwds: Any) -> Any: ...


class PluginConfigSource(NamedTuple):
    type: str
    source: Any


def plugins_dict(module: ModuleType, plugin_type_identifier: str) -> dict[str, type]:
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


T = TypeVar("T")


def load_plugins(
    plugins_dict: dict[str, type[T]],
    plugin_source: PluginConfigSource,
    extra_kwds: dict[str, Any] | None = None,
    plugin_type_keys: Iterable[str] = ("type",),
    dict_to_list_key: str | None = None,
) -> list[T]:
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


def __plugin_classes_in_module(plugin_module: ModuleType) -> Generator[type, None, None]:
    for clazz in getattr(plugin_module, "__all__", []):
        try:
            clazz = getattr(plugin_module, clazz)
        except TypeError:
            clazz = clazz
        yield clazz


def __load_plugins_from_element(
    plugins_dict: dict[str, type[T]], plugins_element, extra_kwds: dict[str, Any]
) -> list[T]:
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
        plugin = __create_plugin_instance(plugin_klazz, plugin_kwds)
        plugins.append(plugin)

    return plugins


def __as_configurable_plugin_instance(obj: Any) -> type[ConfigurablePlugin] | None:
    """Check if the class implements the configurable plugin pattern."""
    try:
        if isinstance(obj, type) and hasattr(obj, "build_template_config"):
            return cast(type[ConfigurablePlugin], obj)
    except TypeError:
        pass
    return None


def __create_plugin_instance(plugin_class: type[T], plugin_kwds: dict[str, Any]) -> T:
    """Create an instance of the plugin class with the provided keyword arguments."""
    if configurable_instance := __as_configurable_plugin_instance(plugin_class):
        plugin_template_config = configurable_instance.build_template_config(**plugin_kwds)
        return cast(T, cast(Any, configurable_instance)(template_config=plugin_template_config))
    else:
        return plugin_class(**plugin_kwds)


def __load_plugins_from_dicts(
    plugins_dict: dict[str, type[T]],
    configs: PluginConfigsT,
    extra_kwds: dict[str, Any],
    plugin_type_keys: Iterable[str],
    dict_to_list_key: str | None,
) -> list[T]:
    plugins = []

    configs_as_list: list[PluginDictConfigT]
    if isinstance(configs, dict) and dict_to_list_key is not None:
        configs_as_list = []
        for key, value in configs.items():
            config = value.copy()
            config[dict_to_list_key] = key
            configs_as_list.append(config)
    else:
        configs_as_list = cast(list[PluginDictConfigT], configs)

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
        plugin_class = plugins_dict[plugin_type]
        plugin = __create_plugin_instance(plugin_class, plugin_kwds)
        plugins.append(plugin)

    return plugins


def plugin_source_from_path(path: StrPath) -> PluginConfigSource:
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


def __read_yaml(path: StrPath):
    if yaml is None:
        raise ImportError("Attempting to read YAML configuration file - but PyYAML dependency unavailable.")

    with open(path, "rb") as f:
        return yaml.safe_load(f)

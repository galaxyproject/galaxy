"""This module is used to parse tool_conf files.

These files define tool lists, sections, labels, etc... the elements of the
Galaxy tool panel.
"""
from abc import (
    ABCMeta,
    abstractmethod,
)

import yaml

from galaxy.util import (
    parse_xml,
    string_as_bool,
)
from galaxy.util.path import StrPath

DEFAULT_MONITOR = False


class ToolConfSource(metaclass=ABCMeta):
    """Interface represents a container of tool references."""

    @abstractmethod
    def parse_items(self):
        """Return a list of ToolConfItem describing source."""

    @abstractmethod
    def parse_tool_path(self):
        """Return tool_path for tools in this toolbox or None."""

    @abstractmethod
    def is_shed_tool_conf(self):
        """Decide if this tool conf is a shed tool conf."""

    def parse_monitor(self):
        """Monitor the toolbox configuration source for changes and reload."""
        return DEFAULT_MONITOR


class XmlToolConfSource(ToolConfSource):
    def __init__(self, config_filename: StrPath):
        tree = parse_xml(config_filename)
        self.root = tree.getroot()

    def parse_tool_path(self):
        return self.root.get("tool_path")

    def parse_tool_cache_data_dir(self):
        return self.root.get("tool_cache_data_dir")

    def parse_items(self):
        return [ensure_tool_conf_item(_) for _ in self.root]

    def is_shed_tool_conf(self):
        has_tool_path = self.parse_tool_path() is not None
        is_shed_conf = string_as_bool(self.root.get("is_shed_conf", "True"))
        return has_tool_path and is_shed_conf

    def parse_monitor(self):
        return string_as_bool(self.root.get("monitor", DEFAULT_MONITOR))


class YamlToolConfSource(ToolConfSource):
    def __init__(self, config_filename: StrPath):
        with open(config_filename) as f:
            as_dict = yaml.safe_load(f)
        self.as_dict = as_dict

    def parse_tool_path(self):
        return self.as_dict.get("tool_path")

    def parse_tool_cache_data_dir(self):
        return self.as_dict.get("tool_cache_data_dir")

    def parse_items(self):
        return [ToolConfItem.from_dict(_) for _ in self.as_dict.get("items")]

    def parse_monitor(self):
        return self.as_dict.get("monitor", DEFAULT_MONITOR)

    def is_shed_tool_conf(self):
        return False


class ToolConfItem:
    """Abstract description of a tool conf item.

    These may include tools, labels, sections, and workflows.
    """

    def __init__(self, type, attributes, elem=None):
        self.type = type
        self.attributes = attributes
        self._elem = elem

    @classmethod
    def from_dict(cls, _as_dict):
        as_dict = _as_dict.copy()
        type = as_dict.get("type")
        del as_dict["type"]
        attributes = as_dict
        if type == "section":
            items = [cls.from_dict(_) for _ in as_dict["items"]]
            del as_dict["items"]
            item = ToolConfSection(attributes, items)
        else:
            item = ToolConfItem(type, attributes)
        return item

    def get(self, key, default=None):
        return self.attributes.get(key, default)

    @property
    def has_elem(self):
        return self._elem is not None

    @property
    def elem(self):
        if self._elem is None:
            raise Exception("item.elem called on toolbox element from non-XML source")
        return self._elem

    @property
    def labels(self):
        labels = None
        if "labels" in self.attributes:
            labels = [label.strip() for label in self.attributes["labels"].split(",")]
        return labels


class ToolConfSection(ToolConfItem):
    def __init__(self, attributes, items, elem=None):
        super().__init__("section", attributes, elem)
        self.items = items


def ensure_tool_conf_item(xml_or_item):
    if xml_or_item is None:
        return None
    elif isinstance(xml_or_item, ToolConfItem):
        return xml_or_item
    elif isinstance(xml_or_item, dict):
        # TODO: handle sections...
        as_dict = xml_or_item.copy()
        type = as_dict.pop("type")
        attributes = as_dict
        return ToolConfItem(type, attributes, None)
    else:
        elem = xml_or_item
        type = elem.tag
        attributes = elem.attrib
        if type != "section":
            return ToolConfItem(type, attributes, elem)
        else:
            items = [ensure_tool_conf_item(_) for _ in elem]
            return ToolConfSection(attributes, items, elem=elem)


def get_toolbox_parser(config_filename: StrPath):
    is_yaml = any(str(config_filename).endswith(e) for e in [".yml", ".yaml", ".json"])
    if is_yaml:
        return YamlToolConfSource(config_filename)
    else:
        return XmlToolConfSource(config_filename)


__all__ = (
    "get_toolbox_parser",
    "ensure_tool_conf_item",
)

from abc import ABCMeta
from abc import abstractmethod

from galaxy.util import parse_xml, string_as_bool
import yaml

DEFAULT_MONITOR = False


class ToolConfSource(object):
    """ This interface represents an abstract source to parse tool
    information from.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def parse_items(self):
        """ Return a list of ToolConfItem
        """

    @abstractmethod
    def parse_tool_path(self):
        """ Return tool_path for tools in this toolbox.
        """

    def parse_monitor(self):
        """ Monitor the toolbox configuration source for changes and
        reload. """
        return DEFAULT_MONITOR


class XmlToolConfSource(ToolConfSource):

    def __init__(self, config_filename):
        tree = parse_xml(config_filename)
        self.root = tree.getroot()

    def parse_tool_path(self):
        return self.root.get('tool_path')

    def parse_items(self):
        return map(ensure_tool_conf_item, self.root.getchildren())

    def parse_monitor(self):
        return string_as_bool(self.root.get('monitor', DEFAULT_MONITOR))


class YamlToolConfSource(ToolConfSource):

    def __init__(self, config_filename):
        with open(config_filename, "r") as f:
            as_dict = yaml.load(f)
        self.as_dict = as_dict

    def parse_tool_path(self):
        return self.as_dict.get('tool_path')

    def parse_items(self):
        return map(ToolConfItem.from_dict, self.as_dict.get('items'))

    def parse_monitor(self):
        return self.as_dict.get('monitor', DEFAULT_MONITOR)


class ToolConfItem(object):
    """ This interface represents an abstract source to parse tool
    information from.
    """

    def __init__(self, type, attributes, elem=None):
        self.type = type
        self.attributes = attributes
        self._elem = elem

    @classmethod
    def from_dict(cls, _as_dict):
        as_dict = _as_dict.copy()
        type = as_dict.get('type')
        del as_dict['type']
        attributes = as_dict
        if type == 'section':
            items = map(cls.from_dict, as_dict['items'])
            del as_dict['items']
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
            labels = [ label.strip() for label in self.attributes["labels"].split( "," ) ]
        return labels


class ToolConfSection(ToolConfItem):

    def __init__(self, attributes, items, elem=None):
        super(ToolConfSection, self).__init__('section', attributes, elem)
        self.items = items


def ensure_tool_conf_item(xml_or_item):
    if xml_or_item is None:
        return None
    elif isinstance(xml_or_item, ToolConfItem):
        return xml_or_item
    else:
        elem = xml_or_item
        type = elem.tag
        attributes = elem.attrib
        if type != "section":
            return ToolConfItem(type, attributes, elem)
        else:
            items = map(ensure_tool_conf_item, elem.getchildren())
            return ToolConfSection(attributes, items, elem=elem)


def get_toolbox_parser(config_filename):
    is_yaml = any(map(lambda e: config_filename.endswith(e), [".yml", ".yaml", ".json"]))
    if is_yaml:
        return YamlToolConfSource(config_filename)
    else:
        return XmlToolConfSource(config_filename)

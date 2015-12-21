from abc import ABCMeta
from abc import abstractmethod

from galaxy.util import parse_xml


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


class XmlToolConfSource(ToolConfSource):

    def __init__(self, config_filename):
        tree = parse_xml(config_filename)
        self.root = tree.getroot()

    def parse_tool_path(self):
        return self.root.get('tool_path')

    def parse_items(self):
        return map(ensure_tool_conf_item, self.root.getchildren())


class ToolConfItem(object):
    """ This interface represents an abstract source to parse tool
    information from.
    """

    def __init__(self, type, attributes, elem=None):
        self.type = type
        self.attributes = attributes
        self._elem = elem

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
    if isinstance(xml_or_item, ToolConfItem):
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
    return XmlToolConfSource(config_filename)

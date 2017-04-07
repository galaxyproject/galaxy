"""Constructors for concrete tool and input source objects."""
from __future__ import absolute_import

import logging

import yaml

from galaxy.tools.loader import load_tool as load_tool_xml
from galaxy.util.odict import odict

from .cwl import CwlToolSource
from .interface import InputSource
from .xml import XmlInputSource, XmlToolSource
from .yaml import YamlToolSource

from ..fetcher import ToolLocationFetcher

log = logging.getLogger(__name__)


def get_tool_source(config_file=None, xml_tree=None, enable_beta_formats=True, tool_location_fetcher=None):
    """Return a ToolSource object corresponding to supplied source.

    The supplied source may be specified as a file path (using the config_file
    parameter) or as an XML object loaded with load_tool_xml.
    """
    if xml_tree is not None:
        return XmlToolSource(xml_tree, source_path=config_file)
    elif config_file is None:
        raise ValueError("get_tool_source called with invalid config_file None.")

    if tool_location_fetcher is None:
        tool_location_fetcher = ToolLocationFetcher()

    config_file = tool_location_fetcher.to_tool_path(config_file)
    if not enable_beta_formats:
        tree = load_tool_xml(config_file)
        return XmlToolSource(tree, source_path=config_file)

    if config_file.endswith(".yml"):
        log.info("Loading tool from YAML - this is experimental - tool will not function in future.")
        with open(config_file, "r") as f:
            as_dict = ordered_load(f)
            return YamlToolSource(as_dict, source_path=config_file)
    elif config_file.endswith(".json") or config_file.endswith(".cwl"):
        log.info("Loading CWL tool - this is experimental - tool likely will not function in future at least in same way.")
        return CwlToolSource(config_file)
    else:
        tree = load_tool_xml(config_file)
        return XmlToolSource(tree, source_path=config_file)


def ordered_load(stream):
    class OrderedLoader(yaml.Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return odict(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)

    return yaml.load(stream, OrderedLoader)


def get_input_source(content):
    """Wrap an XML element in a XmlInputSource if needed.

    If the supplied content is already an InputSource object,
    it is simply returned. This allow Galaxy to uniformly
    consume using the tool input source interface.
    """
    if not isinstance(content, InputSource):
        content = XmlInputSource(content)
    return content


__all__ = ("get_tool_source", "get_input_source")

"""Constructors for concrete tool and input source objects."""

import logging
from typing import (
    Callable,
    Dict,
    List,
    Optional,
)
from uuid import uuid4

from yaml import safe_load

from galaxy.tool_util.cwl.parser import tool_proxy_from_persistent_representation
from galaxy.tool_util.loader import load_tool_with_refereces
from galaxy.util import (
    ElementTree,
    parse_xml_string_to_etree,
)
from galaxy.util.path import StrPath
from galaxy.util.yaml_util import ordered_load
from .cwl import CwlToolSource
from .interface import (
    InputSource,
    ToolSource,
)
from .xml import (
    XmlInputSource,
    XmlToolSource,
)
from .yaml import (
    YamlInputSource,
    YamlToolSource,
)
from ..fetcher import ToolLocationFetcher

log = logging.getLogger(__name__)


def build_xml_tool_source(xml_string: str) -> XmlToolSource:
    return XmlToolSource(parse_xml_string_to_etree(xml_string))


def build_cwl_tool_source(persistent_representation: str) -> CwlToolSource:
    proxy = tool_proxy_from_persistent_representation(persistent_representation)
    return CwlToolSource(tool_proxy=proxy)


def build_yaml_tool_source(yaml_string: str) -> YamlToolSource:
    return YamlToolSource(safe_load(yaml_string))


TOOL_SOURCE_FACTORIES: Dict[str, Callable[[str], ToolSource]] = {
    "XmlToolSource": build_xml_tool_source,
    "YamlToolSource": build_yaml_tool_source,
    "CwlToolSource": build_cwl_tool_source,
}


def get_tool_source(
    config_file: Optional[StrPath] = None,
    xml_tree: Optional[ElementTree] = None,
    enable_beta_formats: bool = True,
    tool_location_fetcher: Optional[ToolLocationFetcher] = None,
    macro_paths: Optional[List[str]] = None,
    strict_cwl_validation: bool = True,
    uuid: Optional[str] = None,
    tool_source_class: Optional[str] = None,
    raw_tool_source: Optional[str] = None,
) -> ToolSource:
    """Return a ToolSource object corresponding to supplied source.

    The supplied source may be specified as a file path (using the config_file
    parameter) or as an XML object loaded with load_tool_with_refereces.
    """
    if xml_tree is not None:
        return XmlToolSource(xml_tree, source_path=config_file, macro_paths=macro_paths)
    elif config_file is None and raw_tool_source is None:
        raise ValueError("get_tool_source called with invalid config_file None.")

    if tool_source_class and raw_tool_source:
        factory = TOOL_SOURCE_FACTORIES[tool_source_class]
        return factory(raw_tool_source)

    if tool_location_fetcher is None:
        tool_location_fetcher = ToolLocationFetcher()

    assert config_file
    config_file = str(config_file)

    config_file = tool_location_fetcher.to_tool_path(config_file)
    if not enable_beta_formats:
        tree, macro_paths = load_tool_with_refereces(config_file)
        return XmlToolSource(tree, source_path=config_file, macro_paths=macro_paths)

    if config_file.endswith(".yml"):
        log.info("Loading tool from YAML - this is experimental - tool will not function in future.")
        with open(config_file) as f:
            as_dict = ordered_load(f)
            return YamlToolSource(as_dict, source_path=config_file)
    elif config_file.endswith(".json") or config_file.endswith(".cwl"):
        log.info(
            "Loading CWL tool [%s]. This is experimental - tool likely will not function in future at least in same way.",
            config_file,
        )
        uuid = uuid or str(uuid4())
        return CwlToolSource(config_file, strict_cwl_validation=strict_cwl_validation, uuid=uuid)
    else:
        tree, macro_paths = load_tool_with_refereces(config_file)
        return XmlToolSource(tree, source_path=config_file, macro_paths=macro_paths)


def get_tool_source_from_representation(
    tool_format, tool_representation, strict_cwl_validation=True, tool_directory=None, uuid=None
):
    # TODO: PRE-MERGE - ensure strict_cwl_validation is being set on caller - ignored right now.
    # TODO: make sure whatever is consuming this method uses ordered load.
    log.info("Loading dynamic tool - this is experimental - tool may not function in future.")
    if tool_format == "GalaxyTool":
        if "version" not in tool_representation:
            tool_representation["version"] = "1.0.0"  # Don't require version for embedded tools.
        return YamlToolSource(tool_representation)
    elif tool_format in ["CommandLineTool", "ExpressionTool"]:
        return CwlToolSource(
            tool_object=tool_representation,
            strict_cwl_validation=strict_cwl_validation,
            tool_directory=tool_directory,
            uuid=uuid,
        )
    else:
        raise Exception(f"Unknown tool representation format [{tool_format}].")


def get_input_source(content):
    """Wrap dicts or XML elements as InputSource if needed.

    If the supplied content is already an InputSource object,
    it is simply returned. This allow Galaxy to uniformly
    consume using the tool input source interface.
    """
    if not isinstance(content, InputSource):
        if isinstance(content, dict):
            content = YamlInputSource(content)
        else:
            content = XmlInputSource(content)
    return content


__all__ = ("get_tool_source", "get_input_source")

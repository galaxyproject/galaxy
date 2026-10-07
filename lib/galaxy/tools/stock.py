"""Reason about stock tools based on ToolSource abstractions."""

from functools import cache
from pathlib import Path

from lxml.etree import XMLSyntaxError

import galaxy.datatypes.converters
import galaxy.tools
from galaxy.tool_util.loader_directory import looks_like_a_tool_xml
from galaxy.tool_util.parser import (
    get_tool_source,
    ToolSource,
)
from galaxy.tool_util.unittest_utils import functional_test_tool_directory
from galaxy.util.resources import files


def stock_tool_paths():
    yield from _walk_directory_for_tools(files(galaxy.tools))
    yield from _walk_directory_for_tools(files(galaxy.datatypes.converters))
    yield from _walk_directory_for_tools(Path(functional_test_tool_directory()))


def stock_tool_sources():
    for stock_tool_path in stock_tool_paths():
        try:
            yield get_tool_source(str(stock_tool_path))
        except XMLSyntaxError:
            continue


def _walk_directory_for_tools(path):
    if path.is_file() and not path.name.endswith("tool_conf.xml") and looks_like_a_tool_xml(path):
        yield path
    elif path.is_dir():
        for directory in path.iterdir():
            yield from _walk_directory_for_tools(directory)


@cache
def stock_tool_sources_by_id() -> dict[str, dict[str, ToolSource]]:
    sources: dict[str, dict[str, ToolSource]] = {}
    for source in stock_tool_sources():
        sources.setdefault(source.parse_id(), {})[source.parse_version()] = source
    return sources

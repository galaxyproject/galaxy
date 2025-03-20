"""Reason about stock tools based on ToolSource abstractions."""

from pathlib import Path

from lxml.etree import XMLSyntaxError

# Set GALAXY_INCLUDES_ROOT from tool shed to point this at a Galaxy root
# (once we are running the tool shed from packages not rooted with Galaxy).
import galaxy.tools
from galaxy.tool_util.loader_directory import looks_like_a_tool_xml
from galaxy.tool_util.parser import get_tool_source
from galaxy.util import galaxy_directory
from galaxy.util.resources import files


def stock_tool_paths():
    yield from _walk_directory_for_tools(files(galaxy.tools))
    yield from _walk_directory_for_tools(Path(galaxy_directory()) / "test" / "functional" / "tools")


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

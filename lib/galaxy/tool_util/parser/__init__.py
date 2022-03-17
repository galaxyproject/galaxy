""" Package responsible for parsing tools from files/abstract tool sources.
"""
from .factory import get_input_source, get_tool_source, get_tool_source_from_representation
from .interface import RequiredFiles, ToolSource
from .output_objects import (
    ToolOutputCollectionPart,
)

__all__ = (
    "get_input_source",
    "get_tool_source",
    "get_tool_source_from_representation",
    "RequiredFiles",
    "ToolOutputCollectionPart",
    "ToolSource",
)

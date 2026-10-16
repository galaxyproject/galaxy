"""FunctionalGetToolInfo: bridges functional test tools to GetToolInfo protocol."""

import os

from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.unittest_utils import (
    functional_test_tool_directory,
    functional_test_tool_source,
)
from galaxy.tool_util_models import ParsedTool


def _find_tool_source(tool_id: str):
    """Find a tool source, searching subdirectories if not found at root."""
    try:
        return functional_test_tool_source(tool_id)
    except OSError:
        pass
    # Search subdirectories
    root = functional_test_tool_directory()
    for dirpath, _dirnames, filenames in os.walk(root):
        for ext in (".xml", ".yml"):
            candidate = f"{tool_id}{ext}"
            if candidate in filenames:
                return get_tool_source(os.path.join(dirpath, candidate))
    raise FileNotFoundError(f"No tool source found for {tool_id}")


class FunctionalGetToolInfo:
    """GetToolInfo backed by functional test tool XMLs."""

    def __init__(self):
        self._cache: dict[str, ParsedTool | None] = {}

    def get_tool_info(self, tool_id: str, tool_version: str | None = None) -> ParsedTool | None:
        if tool_id not in self._cache:
            try:
                ts = _find_tool_source(tool_id)
                self._cache[tool_id] = parse_tool(ts)
            except Exception:
                self._cache[tool_id] = None
        return self._cache[tool_id]

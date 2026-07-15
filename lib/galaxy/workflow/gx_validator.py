""" "A validator for Galaxy workflows that is hooked up to Galaxy internals.

The interface is designed to be usable from the tool shed for external tooling,
but for internal tooling - Galaxy should have its own tool available.
"""

import logging
from typing import (
    Optional,
    TYPE_CHECKING,
)

from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.version import parse_version
from galaxy.tool_util.version_util import AnyVersionT
from galaxy.tool_util.workflow_state import (
    GetToolInfo,
    validate_workflow as validate_workflow_generic,
)
from galaxy.tool_util.workflow_state.toolshed_tool_info import CombinedGetToolInfo
from galaxy.tool_util_models import (
    ParsedTool,
)
from galaxy.tools.stock import stock_tool_sources

if TYPE_CHECKING:
    from galaxy.tool_util.toolbox.base import AbstractToolBox

log = logging.getLogger(__name__)


class GalaxyGetToolInfo(GetToolInfo):
    stock_tools_by_version: dict[str, dict[AnyVersionT, ParsedTool]]
    stock_tools_latest_version: dict[str, AnyVersionT]

    def __init__(self):
        stock_tools: dict[str, dict[AnyVersionT, ParsedTool]] = {}
        stock_tools_latest_version: dict[str, AnyVersionT] = {}
        for stock_tool in stock_tool_sources():
            id = stock_tool.parse_id()
            version = stock_tool.parse_version()
            version_object = None
            if version is not None:
                version_object = parse_version(version)
            if id not in stock_tools:
                stock_tools[id] = {}
                if version_object is not None:
                    stock_tools_latest_version[id] = version_object
            if version_object is not None:
                try:
                    stock_tools[id][version_object] = parse_tool(stock_tool)
                except Exception:
                    pass
            if version_object and version_object > stock_tools_latest_version[id]:
                stock_tools_latest_version[id] = version_object
        self.stock_tools = stock_tools
        self.stock_tools_latest_version = stock_tools_latest_version

    def get_tool_info(self, tool_id: str, tool_version: Optional[str]) -> ParsedTool:
        tool_versions = self.stock_tools.get(tool_id, {})
        if not tool_versions:
            raise KeyError(tool_id)
        if tool_version is not None:
            version_key = parse_version(tool_version)
            if version_key in tool_versions:
                return tool_versions[version_key]
        # Fall back to latest version
        latest_version = self.stock_tools_latest_version[tool_id]
        return tool_versions[latest_version]


class _ToolInputsFromTool:
    """Lightweight ToolInputs wrapper around a live Tool object.

    Avoids re-parsing XML — reuses the already-computed tool.parameters.
    """

    def __init__(self, tool):
        self.inputs = tool.parameters or []


class ToolboxGetToolInfo:
    """GetToolInfo backed by a live Galaxy toolbox.

    Wraps Tool objects as lightweight ToolInputs, reusing already-parsed
    parameters. Falls back to stock_get_tool_info for tools not in the
    toolbox.
    """

    def __init__(self, toolbox: "AbstractToolBox", stock_get_tool_info: Optional[GetToolInfo] = None):
        self.toolbox = toolbox
        self.stock = stock_get_tool_info or GET_TOOL_INFO

    def get_tool_info(self, tool_id: str, tool_version: Optional[str]) -> Optional[ParsedTool]:
        tool = self.toolbox.get_tool(tool_id, tool_version=tool_version)
        if tool is not None and tool.parameters is not None:
            return _ToolInputsFromTool(tool)  # type: ignore[return-value]  # satisfies ToolInputs
        return self.stock.get_tool_info(tool_id, tool_version)


GET_TOOL_INFO = GalaxyGetToolInfo()
GET_TOOL_INFO_WITH_TOOLSHED = CombinedGetToolInfo(GET_TOOL_INFO)


def validate_workflow(as_dict):
    return validate_workflow_generic(as_dict, get_tool_info=GET_TOOL_INFO)

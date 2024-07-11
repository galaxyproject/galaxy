""""A validator for Galaxy workflows that is hooked up to Galaxy internals.

The interface is designed to be usable from the tool shed for external tooling,
but for internal tooling - Galaxy should have its own tool available.
"""

from typing import (
    Dict,
    Optional,
)

from galaxy.tool_util.models import (
    parse_tool,
    ParsedTool,
)
from galaxy.tool_util.version import parse_version
from galaxy.tool_util.version_util import AnyVersionT
from galaxy.tool_util.workflow_state import (
    GetToolInfo,
    validate_workflow as validate_workflow_generic,
)
from galaxy.tools.stock import stock_tool_sources


class GalaxyGetToolInfo(GetToolInfo):
    stock_tools_by_version: Dict[str, Dict[AnyVersionT, ParsedTool]]
    stock_tools_latest_version: Dict[str, AnyVersionT]

    def __init__(self):
        # todo take in a toolbox in the future...
        stock_tools: Dict[str, Dict[AnyVersionT, ParsedTool]] = {}
        stock_tools_latest_version: Dict[str, AnyVersionT] = {}
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
            try:
                stock_tools[id][version_object] = parse_tool(stock_tool)
            except Exception:
                pass
            if version_object and version_object > stock_tools_latest_version[id]:
                stock_tools_latest_version[id] = version_object
        self.stock_tools = stock_tools
        self.stock_tools_latest_version = stock_tools_latest_version

    def get_tool_info(self, tool_id: str, tool_version: Optional[str]) -> ParsedTool:
        if tool_version is not None:
            return self.stock_tools[tool_id][parse_version(tool_version)]
        else:
            latest_verison = self.stock_tools_latest_version[tool_id]
            return self.stock_tools[tool_id][latest_verison]


GET_TOOL_INFO = GalaxyGetToolInfo()


def validate_workflow(as_dict):
    return validate_workflow_generic(as_dict, get_tool_info=GET_TOOL_INFO)

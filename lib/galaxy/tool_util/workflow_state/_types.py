from typing import (
    Any,
    TypeAlias,
)

from typing_extensions import (
    Protocol,
)
from typing import Literal

from galaxy.tool_util.parameters import ToolParameterT
from galaxy.tool_util_models import ParsedTool

NativeWorkflowDict = dict[str, Any]
Format2WorkflowDict = dict[str, Any]
AnyWorkflowDict: TypeAlias = NativeWorkflowDict | Format2WorkflowDict
WorkflowFormat = Literal["gxformat2", "native"]
NativeStepDict = dict[str, Any]
Format2StateDict = dict[str, Any]


class ToolInputs(Protocol):
    """Minimal interface for tool input definitions used in state operations."""

    @property
    def inputs(self) -> list[ToolParameterT]: ...


class GetToolInfo(Protocol):
    """An interface for fetching tool information for steps in a workflow."""

    def get_tool_info(self, tool_id: str, tool_version: str | None) -> ParsedTool | None: ...

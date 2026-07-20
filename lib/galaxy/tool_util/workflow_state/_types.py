from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from typing_extensions import (
    Literal,
    Protocol,
)

from galaxy.tool_util.parameters import ToolParameterT
from galaxy.tool_util_models import ParsedTool

NativeWorkflowDict = Dict[str, Any]
Format2WorkflowDict = Dict[str, Any]
AnyWorkflowDict = Union[NativeWorkflowDict, Format2WorkflowDict]
WorkflowFormat = Literal["gxformat2", "native"]
NativeStepDict = Dict[str, Any]
Format2StateDict = Dict[str, Any]


class ToolInputs(Protocol):
    """Minimal interface for tool input definitions used in state operations."""

    @property
    def inputs(self) -> List[ToolParameterT]: ...


class GetToolInfo(Protocol):
    """An interface for fetching tool information for steps in a workflow."""

    def get_tool_info(self, tool_id: str, tool_version: Optional[str]) -> Optional[ParsedTool]: ...

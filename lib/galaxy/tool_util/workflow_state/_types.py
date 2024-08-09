from typing import (
    Any,
    Dict,
    Union,
)

from typing_extensions import (
    Literal,
    Protocol,
)

from galaxy.tool_util.models import ParsedTool

NativeWorkflowDict = Dict[str, Any]
Format2WorkflowDict = Dict[str, Any]
AnyWorkflowDict = Union[NativeWorkflowDict, Format2WorkflowDict]
WorkflowFormat = Literal["gxformat2", "native"]
NativeStepDict = Dict[str, Any]
Format2StepDict = Dict[str, Any]
NativeToolStateDict = Dict[str, Any]
Format2StateDict = Dict[str, Any]


class GetToolInfo(Protocol):
    """An interface for fetching tool information for steps in a workflow."""

    def get_tool_info(self, tool_id: str, tool_version: str) -> ParsedTool: ...

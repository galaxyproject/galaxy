from ._types import (
    AnyWorkflowDict,
    GetToolInfo,
    WorkflowFormat,
)

from .validation_format2 import validate_workflow_format2
from .validation_native import validate_workflow_native


def validate_workflow(workflow_dict: AnyWorkflowDict, get_tool_info: GetToolInfo):
    if _format(workflow_dict) == "gxformat2":
        validate_workflow_format2(workflow_dict, get_tool_info)
    else:
        validate_workflow_native(workflow_dict, get_tool_info)


def _format(workflow_dict: AnyWorkflowDict) -> WorkflowFormat:
    if workflow_dict.get("a_galaxy_workflow") == "true":
        return "native"
    else:
        return "gxformat2"

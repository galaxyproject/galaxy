import copy
from typing import (
    Optional,
    Union,
)

from gxformat2.normalized import NormalizedNativeWorkflow

from galaxy.tool_util.parameters import WorkflowStepNativeToolState
from galaxy.tool_util_models import ParsedTool
from ._inline_tool import resolve_for_step
from ._state_merge import inject_connections_into_state
from ._types import (
    GetToolInfo,
    NativeWorkflowDict,
    ToolInputs,
)
from ._util import (
    step_input_connections,
    step_tool_state,
    StepLike,
)
from .legacy_parameters import (
    ReplacementClassification,
    scan_native_state,
)


class ReplacementParamsSkip(Exception):
    """Raised when a step contains ${...} replacement parameters that prevent validation."""

    pass


def validate_native_step_against(step: StepLike, parsed_tool: ToolInputs):
    tool_state = step_tool_state(step)
    input_connections = step_input_connections(step)

    # Skip validation entirely if replacement parameters are present —
    # these can't pass type validation (e.g., "${num}" for an integer field)
    scan = scan_native_state(list(parsed_tool.inputs), tool_state, input_connections)
    if scan.classification == ReplacementClassification.YES:
        raise ReplacementParamsSkip("Replacement parameters detected")

    state = copy.deepcopy(tool_state)

    # Inject connection markers for connected params missing their marker
    connections = {key: (val if isinstance(val, list) else [val]) for key, val in input_connections.items()}
    inject_connections_into_state(list(parsed_tool.inputs), state, connections)

    model = WorkflowStepNativeToolState.parameter_model_for(list(parsed_tool.inputs))
    model.model_validate(state)


# -- Public utilities --


def validate_step_native(step: StepLike, get_tool_info: GetToolInfo):
    parsed_tool = get_parsed_tool_for_native_step(step, get_tool_info)
    if parsed_tool is not None:
        validate_native_step_against(step, parsed_tool)


def get_parsed_tool_for_native_step(step: StepLike, get_tool_info: GetToolInfo) -> Optional[ParsedTool]:
    return resolve_for_step(get_tool_info, step)


def validate_workflow_native(
    workflow: "Union[NormalizedNativeWorkflow, NativeWorkflowDict]",
    get_tool_info: GetToolInfo,
):
    if isinstance(workflow, NormalizedNativeWorkflow):
        for step in workflow.steps.values():
            if step.is_subworkflow_step and step.subworkflow:
                validate_workflow_native(step.subworkflow, get_tool_info)
            else:
                validate_step_native(step, get_tool_info)
    else:
        for step_def in workflow["steps"].values():
            if step_def.get("type") == "subworkflow" and "subworkflow" in step_def:
                validate_workflow_native(step_def["subworkflow"], get_tool_info)
            else:
                validate_step_native(step_def, get_tool_info)

import copy
from typing import (
    Dict,
    List,
    Union,
)

from gxformat2.normalized import (
    ensure_format2,
    NormalizedFormat2,
    NormalizedWorkflowStep,
)

from galaxy.tool_util.parameters import (
    ToolParameterT,
    WorkflowStepLinkedToolState,
    WorkflowStepToolState,
)
from ._inline_tool import resolve_for_step
from ._state_merge import inject_connections_into_state
from ._types import (
    Format2WorkflowDict,
    GetToolInfo,
    ToolInputs,
)


def validate_format2_state(
    tool_inputs: List[ToolParameterT],
    state: dict,
    connections: Dict[str, object],
):
    """Validate format2 state + connections against tool definitions.

    1. Validate *state* against ``WorkflowStepToolState``
    2. Deep-copy state, inject ConnectedValue markers for *connections*
    3. Validate merged state against ``WorkflowStepLinkedToolState``

    Raises on validation failure or unmatched connection paths.
    """
    source_model = WorkflowStepToolState.parameter_model_for(tool_inputs)
    if state:
        assert source_model
        source_model.model_validate(state)

    linked_state = copy.deepcopy(state)
    remaining = inject_connections_into_state(tool_inputs, linked_state, dict(connections))

    for key in remaining:
        raise Exception(f"Failed to find parameter definition matching workflow linked key {key}")

    linked_model = WorkflowStepLinkedToolState.parameter_model_for(tool_inputs)
    linked_model.model_validate(linked_state)


def validate_workflow_format2(workflow: Union[Format2WorkflowDict, NormalizedFormat2], get_tool_info: GetToolInfo):
    nf2 = ensure_format2(workflow, expand=True) if not isinstance(workflow, NormalizedFormat2) else workflow
    for step in nf2.steps:
        if step.is_subworkflow_step:
            if isinstance(step.run, NormalizedFormat2):
                validate_workflow_format2(step.run, get_tool_info)
            continue
        validate_step_format2(step, get_tool_info)


def validate_step_format2(step: NormalizedWorkflowStep, get_tool_info: GetToolInfo):
    if not step.is_tool_step:
        return
    parsed_tool = resolve_for_step(get_tool_info, step)
    if parsed_tool is not None:
        validate_step_against(step, parsed_tool)


def validate_step_against(step: NormalizedWorkflowStep, parsed_tool: ToolInputs):
    state = dict(step.state) if step.state else {}

    # Build connect dict from step.in_ (connections already resolved by normalization)
    connect: dict = {}
    for step_input in step.in_:
        if step_input.id and step_input.source:
            src = step_input.source
            connect[step_input.id] = src if isinstance(src, list) else [src]

    validate_format2_state(list(parsed_tool.inputs), state, connect)

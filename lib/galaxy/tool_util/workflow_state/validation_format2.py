from typing import (
    Optional,
    Union,
)

from gxformat2.normalized import (
    ensure_format2,
    NormalizedFormat2,
    NormalizedWorkflowStep,
)

from galaxy.tool_util.parameters import (
    WorkflowStepLinkedToolState,
    WorkflowStepToolState,
)
from ._state_merge import inject_connections_into_state
from ._types import (
    Format2WorkflowDict,
    GetToolInfo,
    ToolInputs,
)


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
    tool_id = step.tool_id
    if not tool_id:
        return
    tool_version: Optional[str] = step.tool_version
    parsed_tool = get_tool_info.get_tool_info(tool_id, tool_version)
    if parsed_tool is not None:
        validate_step_against(step, parsed_tool)


def validate_step_against(step: NormalizedWorkflowStep, parsed_tool: ToolInputs):
    source_tool_state_model = WorkflowStepToolState.parameter_model_for(parsed_tool.inputs)
    linked_tool_state_model = WorkflowStepLinkedToolState.parameter_model_for(parsed_tool.inputs)
    state = dict(step.state) if step.state else {}

    if state:
        assert source_tool_state_model
        source_tool_state_model.model_validate(state)

    # Build connect dict from step.in_ (connections already resolved by normalization)
    connect: dict = {}
    for step_input in step.in_:
        if step_input.id and step_input.source:
            src = step_input.source
            connect[step_input.id] = src if isinstance(src, list) else [src]

    # Merge connections into state for linked validation
    linked_state = dict(state)
    remaining = inject_connections_into_state(list(parsed_tool.inputs), linked_state, connect)

    for key in remaining:
        raise Exception(f"Failed to find parameter definition matching workflow linked key {key}")
    linked_tool_state_model.model_validate(linked_state)

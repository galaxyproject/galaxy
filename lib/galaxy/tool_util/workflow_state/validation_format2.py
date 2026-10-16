import copy

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
from ._state_merge import (
    inject_connections_into_state,
    raise_for_unmatched_connections,
)
from ._types import (
    Format2WorkflowDict,
    GetToolInfo,
    ToolInputs,
)
from ._util import step_when
from .validation_native import validate_native_state


def validate_format2_state(
    tool_inputs: list[ToolParameterT],
    state: dict,
    connections: dict[str, object],
    when_expression: str | None = None,
):
    """Validate format2 state + connections against tool definitions.

    1. Validate *state* against ``WorkflowStepToolState``
    2. Deep-copy state, inject ConnectedValue markers for *connections*
    3. Validate merged state against ``WorkflowStepLinkedToolState``

    Raises on validation failure or unmatched connection paths.  Inputs the
    step's *when_expression* reads are connected to the step rather than to a
    tool parameter, so they are exempt from the unmatched-path check.
    """
    source_model = WorkflowStepToolState.parameter_model_for(tool_inputs)
    if state:
        assert source_model
        source_model.model_validate(state)

    linked_state = copy.deepcopy(state)
    remaining = inject_connections_into_state(tool_inputs, linked_state, dict(connections))
    raise_for_unmatched_connections(remaining, when_expression)

    linked_model = WorkflowStepLinkedToolState.parameter_model_for(tool_inputs)
    linked_model.model_validate(linked_state)


def validate_workflow_format2(workflow: Format2WorkflowDict | NormalizedFormat2, get_tool_info: GetToolInfo):
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
    # Build connect dict from step.in_ (connections already resolved by normalization)
    connect: dict = {}
    for step_input in step.in_:
        if step_input.id and step_input.source:
            src = step_input.source
            connect[step_input.id] = src if isinstance(src, list) else [src]

    # A step carries either a schema-aware ``state`` block or a verbatim native
    # ``tool_state`` block (gxformat2's state-unaware conversion copies the
    # latter). State shape — not workflow format — picks the validator.
    when_expression = step_when(step)
    if not step.state and step.tool_state:
        validate_native_state(list(parsed_tool.inputs), dict(step.tool_state), connect, when_expression)
        return

    state = dict(step.state) if step.state else {}
    validate_format2_state(list(parsed_tool.inputs), state, connect, when_expression)

from typing import (
    cast,
    Optional,
    Union,
)

from gxformat2.normalized import (
    ensure_format2,
    NormalizedFormat2,
    NormalizedWorkflowStep,
)

from galaxy.tool_util.parameters import (
    ConditionalParameterModel,
    ConditionalWhen,
    flat_state_path,
    keys_starting_with,
    repeat_inputs_to_array,
    RepeatParameterModel,
    ToolParameterT,
    validate_explicit_conditional_test_value,
    WorkflowStepLinkedToolState,
    WorkflowStepToolState,
)
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
    for tool_input in parsed_tool.inputs:
        _merge_into_state(connect, tool_input, linked_state)

    for key in connect:
        raise Exception(f"Failed to find parameter definition matching workflow linked key {key}")
    linked_tool_state_model.model_validate(linked_state)


def _merge_into_state(
    connect, tool_input: ToolParameterT, state: dict, prefix: Optional[str] = None, branch_connect=None
):
    if branch_connect is None:
        branch_connect = connect

    name = tool_input.name
    parameter_type = tool_input.parameter_type
    state_path = flat_state_path(name, prefix)
    if parameter_type == "gx_conditional":
        conditional_state = state.get(name, {})
        if name not in state:
            state[name] = conditional_state

        conditional = cast(ConditionalParameterModel, tool_input)
        when: ConditionalWhen = _select_which_when(conditional, conditional_state)
        test_parameter = conditional.test_parameter
        conditional_connect = keys_starting_with(branch_connect, state_path)
        _merge_into_state(
            connect, test_parameter, conditional_state, prefix=state_path, branch_connect=conditional_connect
        )
        for when_parameter in when.parameters:
            _merge_into_state(
                connect, when_parameter, conditional_state, prefix=state_path, branch_connect=conditional_connect
            )
    elif parameter_type == "gx_repeat":
        repeat_state_array = state.get(name, [])
        repeat = cast(RepeatParameterModel, tool_input)
        repeat_instance_connects = repeat_inputs_to_array(state_path, connect)
        for i, repeat_instance_connect in enumerate(repeat_instance_connects):
            while len(repeat_state_array) <= i:
                repeat_state_array.append({})

            repeat_instance_prefix = f"{state_path}_{i}"
            for repeat_parameter in repeat.parameters:
                _merge_into_state(
                    connect,
                    repeat_parameter,
                    repeat_state_array[i],
                    prefix=repeat_instance_prefix,
                    branch_connect=repeat_instance_connect,
                )
        if repeat_state_array and name not in state:
            state[name] = repeat_state_array
    else:
        if state_path in branch_connect:
            state[name] = {"__class__": "ConnectedValue"}
            del connect[state_path]


def _select_which_when(conditional: ConditionalParameterModel, state: dict) -> ConditionalWhen:
    test_parameter = conditional.test_parameter
    test_parameter_name = test_parameter.name
    explicit_test_value = state.get(test_parameter_name)
    test_value = validate_explicit_conditional_test_value(test_parameter_name, explicit_test_value)
    for when in conditional.whens:
        if test_value is None and when.is_default_when:
            return when
        elif test_value == when.discriminator:
            return when
    else:
        raise Exception(f"Invalid conditional test value ({explicit_test_value}) for parameter ({test_parameter_name})")

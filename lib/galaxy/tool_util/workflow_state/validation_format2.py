from typing import (
    cast,
    Optional,
)

from gxformat2.model import (
    get_native_step_type,
    pop_connect_from_step_dict,
    setup_connected_values,
    steps_as_list,
)

from galaxy.tool_util.models import ParsedTool
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
    Format2StepDict,
    Format2WorkflowDict,
    GetToolInfo,
)


def validate_workflow_format2(workflow_dict: Format2WorkflowDict, get_tool_info: GetToolInfo):
    steps = steps_as_list(workflow_dict)
    for step in steps:
        validate_step_format2(step, get_tool_info)


def validate_step_format2(step_dict: Format2StepDict, get_tool_info: GetToolInfo):
    step_type = get_native_step_type(step_dict)
    if step_type != "tool":
        return
    tool_id = cast(str, step_dict.get("tool_id"))
    tool_version: Optional[str] = cast(Optional[str], step_dict.get("tool_version"))
    parsed_tool = get_tool_info.get_tool_info(tool_id, tool_version)
    if parsed_tool is not None:
        validate_step_against(step_dict, parsed_tool)


def validate_step_against(step_dict: Format2StepDict, parsed_tool: ParsedTool):
    source_tool_state_model = WorkflowStepToolState.parameter_model_for(parsed_tool.inputs)
    linked_tool_state_model = WorkflowStepLinkedToolState.parameter_model_for(parsed_tool.inputs)
    contains_format2_state = "state" in step_dict
    contains_native_state = "tool_state" in step_dict
    if contains_format2_state:
        assert source_tool_state_model
        source_tool_state_model.model_validate(step_dict["state"])
    if not contains_native_state:
        if not contains_format2_state:
            step_dict["state"] = {}
        # setup links and then validate against model...
        linked_step = merge_inputs(step_dict, parsed_tool)
        linked_tool_state_model.model_validate(linked_step["state"])


def merge_inputs(step_dict: Format2StepDict, parsed_tool: ParsedTool) -> Format2StepDict:
    connect = pop_connect_from_step_dict(step_dict)
    step_dict = setup_connected_values(step_dict, connect)
    tool_inputs = parsed_tool.inputs

    state_at_level = step_dict["state"]

    for tool_input in tool_inputs:
        _merge_into_state(connect, tool_input, state_at_level)

    for key in connect:
        raise Exception(f"Failed to find parameter definition matching workflow linked key {key}")
    return step_dict


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

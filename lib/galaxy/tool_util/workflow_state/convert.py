from typing import (
    Dict,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.tool_util.models import ParsedTool
from galaxy.tool_util.parameters import ToolParameterT
from ._types import (
    Format2StateDict,
    GetToolInfo,
    NativeStepDict,
)
from .validation_format2 import validate_step_against
from .validation_native import (
    get_parsed_tool_for_native_step,
    native_tool_state,
    validate_native_step_against,
)

Format2InputsDictT = Dict[str, str]


class Format2State(BaseModel):
    state: Format2StateDict
    inputs: Format2InputsDictT = Field(alias="in")


class ConversionValidationFailure(Exception):
    pass


def convert_state_to_format2(native_step_dict: NativeStepDict, get_tool_info: GetToolInfo) -> Format2State:
    parsed_tool = get_parsed_tool_for_native_step(native_step_dict, get_tool_info)
    return convert_state_to_format2_using(native_step_dict, parsed_tool)


def convert_state_to_format2_using(native_step_dict: NativeStepDict, parsed_tool: Optional[ParsedTool]) -> Format2State:
    """Create a "clean" gxformat2 workflow tool state from a native workflow step.

    gxformat2 does not know about tool specifications so it cannot reason about the native
    tool state attribute and just copies it as is. This native state can be pretty ugly. The purpose
    of this function is to build a cleaned up state to replace the gxformat2 copied native tool_state
    with that is more readable and has stronger typing by using the tool's inputs to guide
    the conversion (the parsed_tool parameter).

    This method validates both the native tool state and the resulting gxformat2 tool state
    so that we can be more confident the conversion doesn't corrupt the workflow. If no meta
    model to validate against is supplied or if either validation fails this method throws
    ConversionValidationFailure to signal the caller to just use the native tool state as is
    instead of trying to convert it to a cleaner gxformat2 tool state - under the assumption
    it is better to have an "ugly" workflow than a corrupted one during conversion.
    """
    if parsed_tool is None:
        raise ConversionValidationFailure("Could not resolve tool inputs")
    try:
        validate_native_step_against(native_step_dict, parsed_tool)
    except Exception:
        raise ConversionValidationFailure(
            "Failed to validate native step - not going to convert a tool state that isn't understood"
        )
    result = _convert_valid_state_to_format2(native_step_dict, parsed_tool)
    print(result.dict())
    try:
        validate_step_against(result.dict(), parsed_tool)
    except Exception:
        raise ConversionValidationFailure(
            "Failed to validate resulting cleaned step - not going to convert to an unvalidated tool state"
        )
    return result


def _convert_valid_state_to_format2(native_step_dict: NativeStepDict, parsed_tool: ParsedTool) -> Format2State:
    format2_state: Format2StateDict = {}
    format2_in: Format2InputsDictT = {}

    root_tool_state = native_tool_state(native_step_dict)
    tool_inputs = parsed_tool.inputs
    _convert_state_level(native_step_dict, tool_inputs, root_tool_state, format2_state, format2_in)
    return Format2State(
        **{
            "state": format2_state,
            "in": format2_in,
        }
    )


def _convert_state_level(
    step: NativeStepDict,
    tool_inputs: List[ToolParameterT],
    native_state: dict,
    format2_state_at_level: dict,
    format2_in: Format2InputsDictT,
    prefix: Optional[str] = None,
) -> None:
    prefix = prefix or ""
    assert prefix is not None
    for tool_input in tool_inputs:
        _convert_state_at_level(step, tool_input, native_state, format2_state_at_level, format2_in, prefix)


def _convert_state_at_level(
    step: NativeStepDict,
    tool_input: ToolParameterT,
    native_state_at_level: dict,
    format2_state_at_level: dict,
    format2_in: Format2InputsDictT,
    prefix: str,
) -> None:
    parameter_type = tool_input.parameter_type
    parameter_name = tool_input.name
    value = native_state_at_level.get(parameter_name, None)
    state_path = parameter_name if prefix is None else f"{prefix}|{parameter_name}"
    if parameter_type == "gx_integer":
        # check for runtime input
        format2_value = int(value)
        format2_state_at_level[parameter_name] = format2_value
    elif parameter_type == "gx_data":
        input_connections = step.get("input_connections", {})
        print(state_path)
        print(input_connections)
        if state_path in input_connections:
            format2_in[state_path] = "placeholder"
    else:
        pass
        # raise NotImplementedError(f"Unhandled parameter type {parameter_type}")

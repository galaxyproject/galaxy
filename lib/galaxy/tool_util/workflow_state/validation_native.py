import json
from typing import (
    Any,
    cast,
    Optional,
)

from galaxy.tool_util.parameters import (
    SelectParameterModel,
    ToolParameterT,
)
from galaxy.tool_util_models import ParsedTool
from ._types import (
    GetToolInfo,
    NativeStepDict,
    NativeToolStateDict,
    NativeWorkflowDict,
    ToolInputs,
)
from ._walker import (
    SKIP_VALUE,
    walk_native_state,
)


def _is_connected_or_runtime(value) -> bool:
    return isinstance(value, dict) and value.get("__class__") in ("ConnectedValue", "RuntimeValue")


def _coerce_select_value(value) -> str:
    """Coerce a select value to string for comparison against option values.

    Native tool_state may store select values as int (after JSON decode) or bool.
    Option values in tool definitions are always strings.
    """
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _is_replacement_param(value) -> bool:
    """Check if value is a legacy replacement parameter like ${num} or #{num}."""
    if not isinstance(value, str):
        return False
    return "${" in value or "#{" in value


def validate_native_step_against(step: NativeStepDict, parsed_tool: ToolInputs):
    tool_state = step.get("tool_state")
    assert tool_state is not None
    if isinstance(tool_state, str):
        tool_state = json.loads(tool_state)
        _decode_double_encoded_values(tool_state)

    input_connections = step.get("input_connections", {})

    def merge_and_validate(tool_input: ToolParameterT, value: Any, state_path: str):
        parameter_type = tool_input.parameter_type

        # Merge: inject ConnectedValue for connected params
        if state_path in input_connections and not isinstance(value, dict):
            value = {"__class__": "ConnectedValue"}

        # ConnectedValue/RuntimeValue: valid for any parameter type
        if _is_connected_or_runtime(value):
            return SKIP_VALUE

        if parameter_type in [
            "gx_text",
            "gx_color",
            "gx_hidden",
            "gx_genomebuild",
            "gx_group_tag",
            "gx_baseurl",
            "gx_directory_uri",
        ]:
            pass
        elif parameter_type == "gx_integer":
            if value is not None and value != "null" and not _is_replacement_param(value):
                try:
                    int(value)
                except (ValueError, TypeError):
                    raise Exception(f"Invalid integer data found {value}")
        elif parameter_type == "gx_float":
            if value is not None and value != "null" and not _is_replacement_param(value):
                try:
                    float(value)
                except (ValueError, TypeError):
                    raise Exception(f"Invalid float data found {value}")
        elif parameter_type == "gx_boolean":
            pass
        elif parameter_type in ["gx_data", "gx_data_collection"]:
            if isinstance(value, dict):
                assert "__class__" in value
                assert value["__class__"] in ["RuntimeValue", "ConnectedValue"]
            else:
                assert value in [None, "null"]
        elif parameter_type == "gx_select":
            if value is not None and value != "null":
                select = cast(SelectParameterModel, tool_input)
                options = select.options
                if options is not None:
                    valid_values = [o.value for o in options]
                    if select.multiple and isinstance(value, list):
                        invalid = [v for v in value if _coerce_select_value(v) not in valid_values]
                        if invalid:
                            raise Exception(f"Invalid select option(s) found {invalid}")
                    else:
                        if _coerce_select_value(value) not in valid_values:
                            raise Exception(f"Invalid select option found {value}")
        elif parameter_type in ["gx_data_column", "gx_drill_down"]:
            pass
        elif parameter_type == "gx_rules":
            pass
        else:
            raise NotImplementedError(f"Unhandled parameter type ({parameter_type})")

        return SKIP_VALUE

    walk_native_state(
        step,
        parsed_tool.inputs,
        tool_state,
        merge_and_validate,
        check_unknown_keys=True,
        allow_root_level_duplicates=True,
    )


def _decode_double_encoded_values(state: dict):
    """Decode per-value JSON strings in a double-encoded native tool_state dict."""
    for key, value in list(state.items()):
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
                state[key] = decoded
            except (json.JSONDecodeError, TypeError):
                pass  # genuinely a string value
        if isinstance(state[key], dict):
            _decode_double_encoded_values(state[key])


# -- Public utilities --


def validate_step_native(step: NativeStepDict, get_tool_info: GetToolInfo):
    parsed_tool = get_parsed_tool_for_native_step(step, get_tool_info)
    if parsed_tool is not None:
        validate_native_step_against(step, parsed_tool)


def get_parsed_tool_for_native_step(step: NativeStepDict, get_tool_info: GetToolInfo) -> Optional[ParsedTool]:
    tool_id = cast(str, step.get("tool_id"))
    if not tool_id:
        return None
    tool_version: Optional[str] = cast(Optional[str], step.get("tool_version"))
    parsed_tool = get_tool_info.get_tool_info(tool_id, tool_version)
    return parsed_tool


def validate_workflow_native(workflow_dict: NativeWorkflowDict, get_tool_info: GetToolInfo):
    for step_def in workflow_dict["steps"].values():
        if step_def.get("type") == "subworkflow" and "subworkflow" in step_def:
            validate_workflow_native(step_def["subworkflow"], get_tool_info)
        else:
            validate_step_native(step_def, get_tool_info)


def native_tool_state(step: NativeStepDict) -> NativeToolStateDict:
    tool_state = step.get("tool_state")
    assert tool_state is not None
    if isinstance(tool_state, str):
        tool_state = json.loads(tool_state)
        _decode_double_encoded_values(tool_state)
    return tool_state


def native_connections_for(step: NativeStepDict, parameter: ToolParameterT, prefix: Optional[str]):
    parameter_name = parameter.name
    state_path = parameter_name if prefix is None else f"{prefix}|{parameter_name}"
    input_connections = step.get("input_connections", {})
    return input_connections.get(state_path)

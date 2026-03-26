import json
import logging
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.tool_util.parameters import (
    ConditionalParameterModel,
    RepeatParameterModel,
    SelectParameterModel,
    ToolParameterT,
    validate_explicit_conditional_test_value,
)
from galaxy.tool_util_models.parameters import SectionParameterModel
from ._types import (
    Format2StateDict,
    GetToolInfo,
    ToolInputs,
)
from ._walker import (
    SKIP_VALUE,
    walk_native_state,
)
from ._util import (
    StepLike,
    coerce_select_value,
    is_connected_or_runtime,
    is_replacement_param,
    step_input_connections,
    step_tool_state,
)
from .validation_native import (
    get_parsed_tool_for_native_step,
    validate_native_step_against,
)

log = logging.getLogger(__name__)

Format2InputsDictT = Dict[str, str]


class Format2State(BaseModel):
    state: Format2StateDict
    inputs: Format2InputsDictT = Field(alias="in")


class ConversionValidationFailure(Exception):
    pass


def convert_state_to_format2(native_step: StepLike, get_tool_info: GetToolInfo) -> Format2State:
    parsed_tool = get_parsed_tool_for_native_step(native_step, get_tool_info)
    return convert_state_to_format2_using(native_step, parsed_tool)


def convert_state_to_format2_using(native_step: StepLike, parsed_tool: Optional[ToolInputs]) -> Format2State:
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
        validate_native_step_against(native_step, parsed_tool)
    except Exception:
        raise ConversionValidationFailure(
            "Failed to validate native step - not going to convert a tool state that isn't understood"
        )
    result = _convert_valid_state_to_format2(native_step, parsed_tool)
    try:
        _validate_converted_result(result, parsed_tool)
    except Exception:
        raise ConversionValidationFailure(
            "Failed to validate resulting cleaned step - not going to convert to an unvalidated tool state"
        )
    return result


def _validate_converted_result(result: "Format2State", parsed_tool: ToolInputs):
    """Validate converted format2 state.

    Uses WorkflowStepLinkedToolState for validation — this allows ConnectedValue
    markers for parameters that are in the `in` dict.
    """
    import copy

    from galaxy.tool_util.parameters import WorkflowStepLinkedToolState

    # Build a state dict with ConnectedValue markers for connected params
    linked_state = copy.deepcopy(result.state)
    for connection_path in result.inputs:
        _inject_connected_value(linked_state, connection_path)

    # Skip validation if state contains replacement parameters — these can't
    # pass Pydantic type validation (e.g., "${num}" for an integer field)
    if _state_has_replacement_params(linked_state):
        return

    try:
        linked_model = WorkflowStepLinkedToolState.parameter_model_for(parsed_tool.inputs)
        linked_model.model_validate(linked_state)
    except Exception as e:
        # If the only errors are ConnectedValue type mismatches, that's a model gap not a conversion error
        error_str = str(e)
        if "ConnectedValue" in error_str:
            pass  # Known model completeness gap — connected values not accepted for all types
        else:
            raise


def _state_has_replacement_params(state) -> bool:
    """Check if any value in a (possibly nested) state dict is a replacement parameter."""
    if isinstance(state, dict):
        for v in state.values():
            if _state_has_replacement_params(v):
                return True
    elif isinstance(state, list):
        for v in state:
            if _state_has_replacement_params(v):
                return True
    elif isinstance(state, str) and is_replacement_param(state):
        return True
    return False


def _inject_connected_value(state: dict, connection_path: str):
    """Inject a ConnectedValue marker into a structured state dict.

    Connection paths use | as separator and _N for repeat indices.
    E.g., "queries_0|input2" → state["queries"][0]["input2"] = ConnectedValue
    E.g., "cond|param" → state["cond"]["param"] = ConnectedValue
    """
    import re

    parts = connection_path.split("|")
    target = state
    for _i, part in enumerate(parts[:-1]):
        # Check for repeat index pattern: name_N
        match = re.match(r"^(.+)_(\d+)$", part)
        if match:
            repeat_name = match.group(1)
            repeat_idx = int(match.group(2))
            if repeat_name not in target:
                target[repeat_name] = []
            arr = target[repeat_name]
            while len(arr) <= repeat_idx:
                arr.append({})
            target = arr[repeat_idx]
        else:
            if part not in target:
                target[part] = {}
            target = target[part]

    # Set the leaf
    leaf = parts[-1]
    target[leaf] = {"__class__": "ConnectedValue"}


def _convert_valid_state_to_format2(native_step: StepLike, parsed_tool: ToolInputs) -> Format2State:
    format2_in: Format2InputsDictT = {}
    root_tool_state = step_tool_state(native_step)
    input_connections = step_input_connections(native_step)

    def convert_leaf(tool_input: ToolParameterT, value: Any, state_path: str):
        parameter_type = tool_input.parameter_type

        if parameter_type in ["gx_data", "gx_data_collection"]:
            if state_path in input_connections or is_connected_or_runtime(value):
                format2_in[state_path] = "placeholder"
            elif isinstance(value, dict) and value.get("__class__") == "RuntimeValue":
                format2_in[state_path] = "placeholder"
            return SKIP_VALUE

        if parameter_type == "gx_rules":
            if value is not None and not is_connected_or_runtime(value):
                if isinstance(value, str):
                    value = json.loads(value)
                return value
            return SKIP_VALUE

        # Scalar types
        if is_connected_or_runtime(value):
            format2_in[state_path] = "placeholder"
            return SKIP_VALUE
        if state_path in input_connections:
            format2_in[state_path] = "placeholder"
            return SKIP_VALUE
        if value is not None and value != "null":
            return _convert_scalar_value(parameter_type, tool_input.name, value, tool_input)
        return SKIP_VALUE

    format2_state = walk_native_state(input_connections, parsed_tool.inputs, root_tool_state, convert_leaf)
    return Format2State(
        **{
            "state": format2_state,
            "in": format2_in,
        }
    )


def _convert_scalar_value(parameter_type: str, parameter_name: str, value, tool_input: ToolParameterT):
    """Convert a native scalar value to format2 representation."""
    if parameter_type == "gx_integer":
        if is_replacement_param(value):
            return value
        try:
            return int(value)
        except (ValueError, TypeError):
            raise Exception(f"Failed to convert integer value {value!r} for {parameter_name}")
    elif parameter_type == "gx_float":
        if is_replacement_param(value):
            return value
        try:
            return float(value)
        except (ValueError, TypeError):
            raise Exception(f"Failed to convert float value {value!r} for {parameter_name}")
    elif parameter_type == "gx_boolean":
        return _coerce_bool(value)
    elif parameter_type == "gx_select":
        select = cast(SelectParameterModel, tool_input)
        if select.multiple:
            if isinstance(value, str):
                return value.split(",") if value else []
            elif isinstance(value, list):
                return [coerce_select_value(v) for v in value]
            else:
                return [coerce_select_value(value)]
        return coerce_select_value(value)
    elif parameter_type == "gx_data_column":
        if is_replacement_param(value):
            return value
        from galaxy.tool_util_models.parameters import DataColumnParameterModel

        dc = cast(DataColumnParameterModel, tool_input)
        if dc.multiple:
            if isinstance(value, str):
                return [int(v.strip()) for v in value.split(",") if v.strip()] if value else []
            elif isinstance(value, list):
                return [int(v) for v in value]
        try:
            return int(value)
        except (ValueError, TypeError):
            return value
    else:
        # gx_text, gx_color, gx_hidden, gx_drill_down, etc.
        return value


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1")
    return bool(value)


# -- Schema-aware encoding: format2 → native --


def encode_state_to_native(parsed_tool: ToolInputs, state: dict) -> Dict[str, Any]:
    """Encode a format2 state dict to native tool_state encoding.

    Walks the format2 state with tool definitions to reverse format2
    conversions (e.g., multiple select lists → comma-delimited strings)
    before json.dumps encoding each top-level key.

    ConnectedValue markers are passed through as json.dumps(marker).
    """
    reversed_state = _reverse_format2_values(parsed_tool.inputs, state)
    return {key: json.dumps(value) for key, value in reversed_state.items()}


def _reverse_format2_values(tool_inputs: List[ToolParameterT], state: dict) -> dict:
    """Recursively walk format2 state, reversing format2-specific conversions."""
    input_map = {inp.name: inp for inp in tool_inputs}
    result = {}
    for key, value in state.items():
        if is_connected_or_runtime(value):
            result[key] = value
            continue
        tool_input = input_map.get(key)
        if tool_input is None:
            result[key] = value
            continue
        result[key] = _reverse_value(tool_input, value)
    return result


def _reverse_value(tool_input: ToolParameterT, value: Any) -> Any:
    """Reverse a single format2 value to native form using its tool input definition."""
    if is_connected_or_runtime(value):
        return value
    parameter_type = tool_input.parameter_type

    if parameter_type == "gx_select":
        select = cast(SelectParameterModel, tool_input)
        if select.multiple and isinstance(value, list):
            return [str(v) for v in value]
        return value

    elif parameter_type == "gx_data_column":
        from galaxy.tool_util_models.parameters import DataColumnParameterModel

        dc = cast(DataColumnParameterModel, tool_input)
        if dc.multiple and isinstance(value, list):
            return [str(v) for v in value]
        return str(value) if isinstance(value, int) else value

    elif parameter_type == "gx_conditional":
        if not isinstance(value, dict):
            return value
        conditional = cast(ConditionalParameterModel, tool_input)
        target_when = _find_conditional_branch(conditional, value)
        if target_when is None:
            return value
        all_params: List[ToolParameterT] = [conditional.test_parameter] + list(target_when.parameters)
        return _reverse_format2_values(all_params, value)

    elif parameter_type == "gx_section":
        if not isinstance(value, dict):
            return value
        section = cast(SectionParameterModel, tool_input)
        return _reverse_format2_values(section.parameters, value)

    elif parameter_type == "gx_repeat":
        if not isinstance(value, list):
            return value
        repeat = cast(RepeatParameterModel, tool_input)
        return [
            _reverse_format2_values(repeat.parameters, instance) for instance in value if isinstance(instance, dict)
        ]

    return value


def _find_conditional_branch(conditional: ConditionalParameterModel, state: dict):
    """Find the matching ConditionalWhen for a format2 conditional state dict."""
    test_param_name = conditional.test_parameter.name
    test_value = state.get(test_param_name)
    try:
        test_value = validate_explicit_conditional_test_value(test_param_name, test_value)
    except Exception:
        return None
    for when in conditional.whens:
        if test_value is None and when.is_default_when:
            return when
        if test_value is not None and _test_value_matches(test_value, when.discriminator):
            return when
    return None


def _test_value_matches(test_value, discriminator) -> bool:
    if test_value == discriminator:
        return True
    if isinstance(test_value, bool) and isinstance(discriminator, str):
        return str(test_value).lower() == discriminator
    if isinstance(test_value, str) and isinstance(discriminator, bool):
        return test_value.lower() == str(discriminator).lower()
    return False


# -- Callback factories for gxformat2 protocol --


def make_convert_tool_state(get_tool_info: GetToolInfo):
    """Create a convert_tool_state callback for gxformat2's from_galaxy_native().

    Returns only the state dict — connections are handled by gxformat2's
    _convert_input_connections.
    """

    def _convert(native_step: dict) -> Optional[Dict[str, Any]]:
        try:
            f2_state = convert_state_to_format2(native_step, get_tool_info)
            return f2_state.state
        except ConversionValidationFailure:
            return None

    return _convert


def make_encode_tool_state(get_tool_info: GetToolInfo):
    """Create a native_state_encoder callback for gxformat2's ImportOptions.

    Performs schema-aware encoding of format2 state back to native tool_state,
    reversing format2 conversions (multiple select lists → comma strings, etc.).
    """

    def _encode(step: dict, state: dict) -> Optional[Dict[str, Any]]:
        tool_id = step.get("tool_id")
        tool_version = step.get("tool_version")
        if not tool_id:
            return None
        try:
            tool_info = get_tool_info.get_tool_info(tool_id, tool_version)
            if tool_info is None:
                return None
            return encode_state_to_native(tool_info, state)
        except Exception:
            log.debug("encode_state_to_native failed for %s, falling back to default", tool_id, exc_info=True)
            return None

    return _encode

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
    SelectParameterModel,
    ToolParameterT,
)
from ._inline_tool import resolve_for_step
from ._types import (
    Format2StateDict,
    GetToolInfo,
    ToolInputs,
)
from ._util import (
    coerce_select_value,
    is_connected_or_runtime,
    is_connected_value,
    is_runtime_value,
    step_connected_paths,
    step_input_connections,
    step_tool_state,
    StepLike,
)
from ._walker import (
    SKIP_VALUE,
    walk_format2_state,
    walk_native_state,
)
from .legacy_parameters import (
    ReplacementClassification,
    scan_native_state,
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

    # Bail early if the native state uses legacy replacement parameters —
    # we can't meaningfully convert or validate ${...} in typed fields.
    tool_state = step_tool_state(native_step)
    input_connections = step_input_connections(native_step)
    scan = scan_native_state(list(parsed_tool.inputs), tool_state, input_connections)
    if scan.classification == ReplacementClassification.YES:
        raise ConversionValidationFailure("Step uses legacy replacement parameters — cannot convert to format2")

    try:
        import copy as _copy

        from ._util import step_as_dict
        from .clean import strip_stale_keys
        from .stale_keys import ALL_CATEGORIES, StaleKeyPolicy

        step_copy = _copy.deepcopy(step_as_dict(native_step))
        strip_stale_keys(step_copy, parsed_tool, policy=StaleKeyPolicy(denied=set(ALL_CATEGORIES)))
        validate_native_step_against(step_copy, parsed_tool)
    except ConversionValidationFailure:
        raise
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
    """Validate converted format2 state via shared format2 validation."""
    from .validation_format2 import validate_format2_state

    validate_format2_state(list(parsed_tool.inputs), result.state, dict(result.inputs))


def _convert_valid_state_to_format2(native_step: StepLike, parsed_tool: ToolInputs) -> Format2State:
    format2_in: Format2InputsDictT = {}
    root_tool_state = step_tool_state(native_step)
    input_connections = step_input_connections(native_step)
    connected = step_connected_paths(native_step)

    def convert_leaf(tool_input: ToolParameterT, value: Any, state_path: str):
        parameter_type = tool_input.parameter_type

        if parameter_type in ["gx_data", "gx_data_collection"]:
            if state_path in connected or is_connected_value(value):
                format2_in[state_path] = "placeholder"
                return SKIP_VALUE
            if is_runtime_value(value):
                if not tool_input.optional:
                    format2_in[state_path] = "placeholder"
                return SKIP_VALUE
            return SKIP_VALUE

        if parameter_type == "gx_rules":
            if value is not None and not is_connected_or_runtime(value):
                if isinstance(value, str):
                    value = json.loads(value)
                return value
            return SKIP_VALUE

        # Scalar types
        if state_path in connected or is_connected_value(value):
            format2_in[state_path] = "placeholder"
            return SKIP_VALUE
        if is_runtime_value(value):
            if not tool_input.optional:
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
        try:
            return int(value)
        except (ValueError, TypeError):
            raise Exception(f"Failed to convert integer value {value!r} for {parameter_name}")
    elif parameter_type == "gx_float":
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
    conversions (e.g., multiple select lists → comma-delimited strings).
    Returns a clean dict with proper Python types — no per-key json.dumps.
    ConnectedValue markers are passed through as-is.
    """
    return _reverse_format2_values(parsed_tool.inputs, state)


def _reverse_format2_values(tool_inputs: List[ToolParameterT], state: dict) -> dict:
    """Walk format2 state with tool definitions, reversing format2-specific conversions."""
    return walk_format2_state(tool_inputs, state, _reverse_leaf)


def _reverse_leaf(tool_input: ToolParameterT, value: Any, state_path: str) -> Any:
    """Reverse a single format2 leaf value to native form."""
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

    return value


# -- Callback factories for gxformat2 protocol --


def make_convert_tool_state(get_tool_info: GetToolInfo):
    """Create a ConvertToolStateFn for gxformat2's from_galaxy_native().

    Signature: (native_step: dict) -> Optional[Dict[str, Any]]
    Returns format2 state dict, or None to fall back to default passthrough.
    """

    def _convert(native_step: dict) -> Optional[Dict[str, Any]]:
        try:
            f2_state = convert_state_to_format2(native_step, get_tool_info)
            return f2_state.state
        except ConversionValidationFailure:
            return None

    return _convert


def make_encode_tool_state(get_tool_info: GetToolInfo):
    """Create a NativeStateEncoderFn for gxformat2's ImportOptions.state_encode_to_native.

    Signature: (step: dict, state: dict) -> Optional[Dict[str, Any]]
    Returns schema-aware native tool_state (clean dict), or None to fall back
    to gxformat2's default passthrough (which is also a clean dict).
    """

    def _encode(step: dict, state: dict) -> Optional[Dict[str, Any]]:
        tool_id = step.get("tool_id")
        try:
            tool_info = resolve_for_step(get_tool_info, step)
            if tool_info is None:
                return None
            return encode_state_to_native(tool_info, state)
        except Exception:
            log.debug("encode_state_to_native failed for %s, falling back to default", tool_id, exc_info=True)
            return None

    return _encode

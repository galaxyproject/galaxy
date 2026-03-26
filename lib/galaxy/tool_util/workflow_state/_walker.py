"""Shared tree walker for native Galaxy workflow tool state.

Handles the recursive traversal of native tool state dicts, including:
- Conditional branch selection
- Repeat instance expansion from input_connections
- Section/container JSON string decoding
- Unknown key checking for validation

Used by both convert.py (building format2 state) and
validation_native.py (merge + validate in one pass).
"""

import json
from typing import (
    cast,
    List,
    Optional,
)

from galaxy.tool_util.parameters import (
    ConditionalParameterModel,
    ConditionalWhen,
    flat_state_path,
    repeat_inputs_to_array,
    RepeatParameterModel,
    ToolParameterT,
    validate_explicit_conditional_test_value,
)
from galaxy.tool_util_models.parameters import SectionParameterModel


def _collect_all_parameter_names(tool_inputs: List[ToolParameterT]) -> frozenset:
    """Collect all parameter names from the full tool input tree, across all conditional branches.

    Used to identify unknown root keys that are duplicates leaked by the Galaxy
    serialization bug (params_to_strings passes through all keys, not just declared inputs).
    """
    names: set = set()
    for tool_input in tool_inputs:
        names.add(tool_input.name)
        parameter_type = tool_input.parameter_type
        if parameter_type == "gx_conditional":
            conditional = cast(ConditionalParameterModel, tool_input)
            names.add(conditional.test_parameter.name)
            for when in conditional.whens:
                names |= _collect_all_parameter_names(list(when.parameters))
        elif parameter_type == "gx_repeat":
            repeat = cast(RepeatParameterModel, tool_input)
            names |= _collect_all_parameter_names(list(repeat.parameters))
        elif parameter_type == "gx_section":
            section = cast(SectionParameterModel, tool_input)
            names |= _collect_all_parameter_names(list(section.parameters))
    return frozenset(names)


class _SkipValue:
    """Sentinel returned by leaf callbacks to omit a value from the walker's output dict."""

    pass


SKIP_VALUE = _SkipValue()

_NATIVE_BOOKKEEPING_KEYS = frozenset(
    {
        "__current_case__",
        "__index__",
        "__input_ext",
        "__page__",
        "__rerun_remap_job_id__",
        "__job_resource",
        "chromInfo",
    }
)


# TODO: Come up with a read type of leaf_callback
def walk_native_state(
    input_connections: dict,
    tool_inputs: List[ToolParameterT],
    state: dict,
    leaf_callback,  # (tool_input: ToolParameterT, value: Any, state_path: str) -> Any | _SkipValue
    prefix: Optional[str] = None,
    check_unknown_keys: bool = False,
    allow_root_level_duplicates: bool = False,
    _all_parameter_names: Optional[frozenset] = None,
) -> dict:
    """Walk native tool state tree, calling leaf_callback for each leaf parameter.

    Handles: conditional branch selection (with __current_case__ fallback),
    repeat instance expansion from input_connections, section/container JSON decode.

    Returns dict of {param_name: callback_result} for non-skipped leaves,
    with nested dicts for conditionals/sections and lists for repeats.

    When check_unknown_keys=True, raises on state keys not matching any tool input
    or known bookkeeping key, and raises on malformed container values (non-dict
    conditionals/sections, non-list repeats).

    When allow_root_level_duplicates=True (requires check_unknown_keys=True), unknown
    keys at the root level are tolerated if they match a parameter name found anywhere
    in the tool's input tree. This handles the Galaxy serialization bug where
    params_to_strings() leaks conditional/section params to root level.
    """
    output: dict = {}

    if check_unknown_keys:
        known = {inp.name for inp in tool_inputs}
        for key in state:
            if key not in known and key not in _NATIVE_BOOKKEEPING_KEYS:
                if allow_root_level_duplicates and prefix is None:
                    if _all_parameter_names is None:
                        _all_parameter_names = _collect_all_parameter_names(tool_inputs)
                    if key in _all_parameter_names:
                        continue
                raise Exception(f"Unknown key found {key}, failing state validation")

    for tool_input in tool_inputs:
        parameter_type = tool_input.parameter_type
        parameter_name = tool_input.name
        value = state.get(parameter_name, None)
        state_path = flat_state_path(parameter_name, prefix)

        if parameter_type == "gx_conditional":
            conditional = cast(ConditionalParameterModel, tool_input)
            conditional_state = as_dict(value)
            if conditional_state is None:
                if check_unknown_keys and value is not None:
                    raise Exception(f"Invalid conditional state found {value!r} for conditional {parameter_name}")
                continue
            target_when = _select_which_when_native(conditional, conditional_state)
            if target_when is None:
                all_params: List[ToolParameterT] = [conditional.test_parameter]
            else:
                all_params = [conditional.test_parameter] + list(target_when.parameters)
            nested = walk_native_state(
                input_connections,
                all_params,
                conditional_state,
                leaf_callback,
                prefix=state_path,
                check_unknown_keys=check_unknown_keys,
            )
            if nested:
                output[parameter_name] = nested

        elif parameter_type == "gx_repeat":
            repeat = cast(RepeatParameterModel, tool_input)
            repeat_state = as_list(value)
            if check_unknown_keys and value is not None and not repeat_state and not isinstance(value, list):
                # _as_list returned [] but value was non-None and not already a list —
                # could be a string that didn't decode to a list, or some other type
                if isinstance(value, str):
                    try:
                        decoded = json.loads(value)
                        if not isinstance(decoded, list):
                            raise Exception(f"Invalid repeat state found {value!r} for repeat {parameter_name}")
                    except (json.JSONDecodeError, TypeError):
                        raise Exception(f"Invalid repeat state found {value!r} for repeat {parameter_name}")
                else:
                    raise Exception(f"Invalid repeat state found {value!r} for repeat {parameter_name}")
            repeat_instance_connects = repeat_inputs_to_array(state_path, input_connections)
            max_instances = max(len(repeat_state), len(repeat_instance_connects))
            while len(repeat_state) < max_instances:
                repeat_state.append({})
            result_array = []
            for i, instance in enumerate(repeat_state):
                instance_prefix = f"{state_path}_{i}"
                nested = walk_native_state(
                    input_connections,
                    repeat.parameters,
                    instance,
                    leaf_callback,
                    prefix=instance_prefix,
                    check_unknown_keys=check_unknown_keys,
                )
                result_array.append(nested)
            if result_array:
                output[parameter_name] = result_array

        elif parameter_type == "gx_section":
            section = cast(SectionParameterModel, tool_input)
            section_state = as_dict(value)
            if section_state is None:
                if check_unknown_keys and value is not None:
                    raise Exception(f"Invalid section state found {value!r} for section {parameter_name}")
                continue
            nested = walk_native_state(
                input_connections,
                section.parameters,
                section_state,
                leaf_callback,
                prefix=state_path,
                check_unknown_keys=check_unknown_keys,
            )
            if nested:
                output[parameter_name] = nested

        else:
            result = leaf_callback(tool_input, value, state_path)
            if not isinstance(result, _SkipValue):
                output[parameter_name] = result

    return output


# TODO: we need to be much more targetted here I think - can we let those exceptions bubble up on IWC
# workflows?
def as_dict(value) -> Optional[dict]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, dict):
                return decoded
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def as_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, list):
                return decoded
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def _test_value_matches_discriminator(test_value, discriminator) -> bool:
    """Compare test value against when discriminator, handling bool/string coercion.

    Native tool_state double-encoding means json.loads("true") produces Python True (bool),
    but gx_select conditional discriminators are always strings ("true"/"false").
    gx_boolean discriminators are actual bools. Handle both cases.
    """
    if test_value == discriminator:
        return True
    if isinstance(test_value, bool) and isinstance(discriminator, str):
        return str(test_value).lower() == discriminator
    if isinstance(test_value, str) and isinstance(discriminator, bool):
        return test_value.lower() == str(discriminator).lower()
    return False


def _select_which_when_native(
    conditional: ConditionalParameterModel, conditional_state: dict
) -> Optional[ConditionalWhen]:
    """Select which conditional branch matches the test parameter value.

    Returns None when no branch matches (e.g., boolean conditional set to
    false with only a <when value="true"> branch — the conditional is inactive).
    """
    test_parameter = conditional.test_parameter
    test_parameter_name = test_parameter.name
    explicit_test_value = conditional_state.get(test_parameter_name)
    test_value = validate_explicit_conditional_test_value(test_parameter_name, explicit_test_value)

    for when in conditional.whens:
        if test_value is None and when.is_default_when:
            return when
        elif test_value is not None and _test_value_matches_discriminator(test_value, when.discriminator):
            return when

    # No branch matched — try default when as fallback
    for when in conditional.whens:
        if when.is_default_when:
            return when

    return None

"""Shared tree walkers for Galaxy workflow tool state.

Two walkers for the two serialization formats:

- ``walk_native_state()`` — native (.ga) tool_state with double-encoding,
  ``input_connections``-driven repeat sizing, bookkeeping key stripping, and
  unknown-key checking.  Used by convert.py and validation_native.py.

- ``walk_format2_state()`` — format2 (.gxwf.yml) structured state dicts.
  Clean dicts/lists, no bookkeeping.  Used by convert.py for post-conversion
  validation and reverse encoding.
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


# These json.loads() calls are safe because they are only called by the walker
# for values the tool schema identifies as containers (conditional, section, repeat).
# Container values in native tool_state are always JSON-encoded dicts or lists —
# there is no ambiguity like there is for leaf values (where "2" could be the
# string "2" or a JSON-encoded integer). Leaf values are never passed through
# these functions; they go directly to the walker's leaf_callback for
# type-aware handling.
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


# -- Format2 state walker --


def walk_format2_state(
    tool_inputs: List[ToolParameterT],
    state: dict,
    leaf_callback,  # (tool_input: ToolParameterT, value: Any, state_path: str) -> Any | _SkipValue
    prefix: Optional[str] = None,
) -> dict:
    """Walk a format2 structured state dict, calling leaf_callback for each leaf parameter.

    Handles conditionals (branch selection via test value), repeats (list of
    instance dicts), and sections (nested dicts).  No double-encoding, no
    bookkeeping keys, no input_connections — format2 state is already clean.

    Returns dict of {param_name: callback_result} for non-skipped leaves,
    with nested dicts for conditionals/sections and lists for repeats.
    """
    output: dict = {}

    input_map = {inp.name: inp for inp in tool_inputs}
    for key, value in state.items():
        tool_input = input_map.get(key)
        if tool_input is None:
            # Preserve keys not in tool definition — may be extra metadata,
            # version-skew remnants, etc.  Only declared params get walked.
            output[key] = value
            continue
        state_path = flat_state_path(key, prefix)
        result = _walk_format2_value(tool_input, value, state_path, leaf_callback)
        if not isinstance(result, _SkipValue):
            output[key] = result

    return output


def _walk_format2_value(tool_input: ToolParameterT, value, state_path: str, leaf_callback):
    """Recurse into a single format2 value guided by its tool input definition."""
    parameter_type = tool_input.parameter_type

    if parameter_type == "gx_conditional":
        if not isinstance(value, dict):
            return leaf_callback(tool_input, value, state_path)
        conditional = cast(ConditionalParameterModel, tool_input)
        # TODO: research whether select_which_when_format2 can be unified
        # with _select_which_when_native — they are nearly identical but the
        # native version has a default-when fallback pass.
        target_when = select_which_when_format2(conditional, value)
        if target_when is None:
            all_params: List[ToolParameterT] = [conditional.test_parameter]
        else:
            all_params = [conditional.test_parameter] + list(target_when.parameters)
        nested = walk_format2_state(all_params, value, leaf_callback, prefix=state_path)
        return nested if nested else SKIP_VALUE

    elif parameter_type == "gx_section":
        if not isinstance(value, dict):
            return leaf_callback(tool_input, value, state_path)
        section = cast(SectionParameterModel, tool_input)
        nested = walk_format2_state(section.parameters, value, leaf_callback, prefix=state_path)
        return nested if nested else SKIP_VALUE

    elif parameter_type == "gx_repeat":
        if not isinstance(value, list):
            return leaf_callback(tool_input, value, state_path)
        repeat = cast(RepeatParameterModel, tool_input)
        result_array = []
        for i, instance in enumerate(value):
            if not isinstance(instance, dict):
                continue
            instance_prefix = f"{state_path}_{i}"
            nested = walk_format2_state(repeat.parameters, instance, leaf_callback, prefix=instance_prefix)
            result_array.append(nested)
        return result_array if result_array else SKIP_VALUE

    else:
        return leaf_callback(tool_input, value, state_path)


def select_which_when_format2(conditional: ConditionalParameterModel, state: dict) -> Optional[ConditionalWhen]:
    """Select the matching ConditionalWhen for a format2 conditional state dict."""
    test_param_name = conditional.test_parameter.name
    test_value = state.get(test_param_name)
    try:
        test_value = validate_explicit_conditional_test_value(test_param_name, test_value)
    except Exception:
        return None
    for when in conditional.whens:
        if test_value is None and when.is_default_when:
            return when
        if test_value is not None and _test_value_matches_discriminator(test_value, when.discriminator):
            return when
    return None

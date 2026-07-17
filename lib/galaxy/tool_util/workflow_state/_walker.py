"""Shared tree walkers for Galaxy workflow tool state.

Two walkers for the two serialization formats:

- ``walk_native_state()`` — native (.ga) tool_state with double-encoding,
  ``input_connections``-driven repeat sizing, bookkeeping key stripping, and
  unknown-key checking.  Used by convert.py and validation_native.py.

- ``walk_format2_state()`` — format2 (.gxwf.yml) structured state dicts.
  Clean dicts/lists, no bookkeeping.  Used by convert.py for post-conversion
  validation and reverse encoding.
"""

from collections.abc import Callable
from typing import (
    Any,
    cast,
)

from galaxy.tool_util.parameters import (
    active_branch_params,
    ConditionalParameterModel,
    ConditionalWhen,
    flat_state_path,
    NATIVE_BOOKKEEPING_KEYS,
    repeat_inputs_to_array,
    RepeatParameterModel,
    select_which_when_native,
    ToolParameterT,
)
from galaxy.tool_util_models.parameters import SectionParameterModel


def _collect_all_parameter_names(tool_inputs: list[ToolParameterT]) -> frozenset:
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

LeafCallback = Callable[[ToolParameterT, Any, str], Any | _SkipValue]

_NATIVE_BOOKKEEPING_KEYS = NATIVE_BOOKKEEPING_KEYS


def walk_native_state(
    input_connections: dict,
    tool_inputs: list[ToolParameterT],
    state: dict,
    leaf_callback: LeafCallback,
    prefix: str | None = None,
    check_unknown_keys: bool = False,
    allow_root_level_duplicates: bool = False,
    _all_parameter_names: frozenset | None = None,
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
            if not isinstance(value, dict):
                if check_unknown_keys and value is not None:
                    raise Exception(f"Invalid conditional state found {value!r} for conditional {parameter_name}")
                continue
            conditional_state = value
            all_params = active_branch_params(conditional, conditional_state)
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
            if isinstance(value, list):
                repeat_state = value
            else:
                if check_unknown_keys and value is not None:
                    raise Exception(f"Invalid repeat state found {value!r} for repeat {parameter_name}")
                repeat_state = []
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
            if not isinstance(value, dict):
                if check_unknown_keys and value is not None:
                    raise Exception(f"Invalid section state found {value!r} for section {parameter_name}")
                continue
            section_state = value
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


# -- Format2 state walker --


def walk_format2_state(
    tool_inputs: list[ToolParameterT],
    state: dict,
    leaf_callback: LeafCallback,
    prefix: str | None = None,
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


def _walk_format2_value(tool_input: ToolParameterT, value: Any, state_path: str, leaf_callback: LeafCallback):
    """Recurse into a single format2 value guided by its tool input definition."""
    parameter_type = tool_input.parameter_type

    if parameter_type == "gx_conditional":
        if not isinstance(value, dict):
            return leaf_callback(tool_input, value, state_path)
        conditional = cast(ConditionalParameterModel, tool_input)
        target_when = select_which_when_format2(conditional, value)
        if target_when is None:
            all_params: list[ToolParameterT] = [conditional.test_parameter]
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


def select_which_when_format2(conditional: ConditionalParameterModel, state: dict) -> ConditionalWhen | None:
    """Select the matching ConditionalWhen for a format2 conditional state dict.

    Delegates to select_which_when_native (same matching logic + default-when
    fallback), but suppresses validation errors for graceful degradation.
    """
    try:
        return select_which_when_native(conditional, state)
    except Exception:
        return None

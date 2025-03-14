"""There is some shared logic between matching/multiplying inputs in workflows
and tools. This module is meant to capture some general permutation logic that
can be applicable for both cases but will only be used in the newer tools case
first.

Maybe this doesn't make sense and maybe much of this stuff could be replaced
with itertools product and permutations. These are open questions.
"""

import copy
from typing import Tuple

from galaxy.exceptions import MessageException
from galaxy.util.bunch import Bunch

input_classification = Bunch(
    SINGLE="single",
    MATCHED="matched",
    MULTIPLIED="multiplied",
)


class InputMatchedException(MessageException):
    """Indicates problem matching inputs while building up inputs
    permutations."""


def build_combos(single_inputs, matched_multi_inputs, multiplied_multi_inputs, nested):
    # Build up every combination of inputs to be run together.
    input_combos = __extend_with_matched_combos(single_inputs, matched_multi_inputs, nested)
    input_combos = __extend_with_multiplied_combos(input_combos, multiplied_multi_inputs, nested)
    return input_combos


def __extend_with_matched_combos(single_inputs, multi_inputs, nested):
    """

    {a => 1, b => 2} and {c => {3, 4}, d => {5, 6}}

    Becomes

    [ {a => 1, b => 2, c => 3, d => 5}, {a => 1, b => 2, c => 4, d => 6}, ]

    """

    if len(multi_inputs) == 0:
        return [single_inputs]

    matched_multi_inputs = []

    first_multi_input_key = next(iter(multi_inputs.keys()))
    first_multi_value = multi_inputs.get(first_multi_input_key)

    for value in first_multi_value:
        new_inputs = __copy_and_extend_inputs(single_inputs, first_multi_input_key, value, nested=nested)
        matched_multi_inputs.append(new_inputs)

    for multi_input_key, multi_input_values in multi_inputs.items():
        if multi_input_key == first_multi_input_key:
            continue
        if len(multi_input_values) != len(first_multi_value):
            raise InputMatchedException(
                f"Received {len(multi_input_values)} inputs for '{multi_input_key}' and {len(first_multi_value)} inputs for '{first_multi_input_key}', these should be of equal length"
            )

        for index, value in enumerate(multi_input_values):
            state_set_value(matched_multi_inputs[index], multi_input_key, value, nested)

    return matched_multi_inputs


def __extend_with_multiplied_combos(input_combos, multi_inputs, nested):
    combos = input_combos

    for multi_input_key, multi_input_value in multi_inputs.items():
        iter_combos = []

        for combo in combos:
            for input_value in multi_input_value:
                iter_combo = __copy_and_extend_inputs(combo, multi_input_key, input_value, nested)
                iter_combos.append(iter_combo)

        combos = iter_combos

    return combos


def __copy_and_extend_inputs(inputs, key, value, nested):
    # can't deepcopy dicts with our models for reason I don't understand,
    # test_map_over_two_collections_unlinked breaks if I try to combine these two branches of the if
    new_inputs = state_copy(inputs, nested)
    state_set_value(new_inputs, key, value, nested)
    return new_inputs


def state_copy(inputs, nested):
    # can't deepcopy dicts with our models for reason I don't understand,
    # test_map_over_two_collections_unlinked breaks if I try to combine these two branches of the if
    if nested:
        state_dict_copy = copy.deepcopy(inputs)
    else:
        state_dict_copy = dict(inputs)
    return state_dict_copy


def state_set_value(state_dict, key, value, nested):
    if "|" not in key or not nested:
        state_dict[key] = value
    else:
        first, rest = key.split("|", 1)
        if first not in state_dict and looks_like_flattened_repeat_key(first):
            repeat_name, index = split_flattened_repeat_key(first)
            if repeat_name not in state_dict:
                state_dict[repeat_name] = []
            repeat_state = state_dict[repeat_name]
            while len(repeat_state) <= index:
                repeat_state.append({})
            state_set_value(repeat_state[index], rest, value, nested)
        else:
            state_set_value(state_dict[first], rest, value, nested)


def state_remove_value(state_dict, key, nested):
    if "|" not in key or not nested:
        del state_dict[key]
    else:
        first, rest = key.split("|", 1)
        child_dict = state_dict[first]
        # repeats?
        if "|" in rest:
            state_remove_value(child_dict, rest, nested)
        else:
            del child_dict[rest]
            if len(child_dict) == 0:
                del state_dict[first]


def state_get_value(state_dict, key, nested):
    if "|" not in key or not nested:
        return state_dict[key]
    else:
        first, rest = key.split("|", 1)
        if first not in state_dict and looks_like_flattened_repeat_key(first):
            repeat_name, index = split_flattened_repeat_key(first)
            return state_get_value(state_dict[repeat_name][index], rest, nested)
        else:
            return state_get_value(state_dict[first], rest, nested)


def is_in_state(state_dict, key, nested):
    if not state_dict:
        return False
    if "|" not in key or not nested:
        return key in state_dict
    else:
        first, rest = key.split("|", 1)
        # repeats?
        is_in_state(state_dict.get(first), rest, nested)


def looks_like_flattened_repeat_key(key: str) -> bool:
    return key.rsplit("_", 1)[-1].isdigit()


def split_flattened_repeat_key(key: str) -> Tuple[str, int]:
    input_name, _index = key.rsplit("_", 1)
    index = int(_index)
    return input_name, index

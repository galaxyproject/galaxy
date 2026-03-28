"""Shared function for injecting ConnectedValue markers into format2 state dicts.

Walks the parameter tree to match pipe-separated connection paths
(e.g. ``queries_0|input2``) to tool parameters.  Handles conditionals,
repeats, and sections.  Used by both convert.py (post-conversion
validation) and validation_format2.py (standalone format2 validation).
"""

from typing import (
    cast,
    Dict,
    List,
    Optional,
)

from galaxy.tool_util.parameters import (
    ConditionalParameterModel,
    flat_state_path,
    keys_starting_with,
    repeat_inputs_to_array,
    RepeatParameterModel,
    ToolParameterT,
)
from galaxy.tool_util_models.parameters import SectionParameterModel

from ._walker import select_which_when_format2


def inject_connections_into_state(
    tool_inputs: List[ToolParameterT],
    state: dict,
    connections: Dict[str, object],
) -> Dict[str, object]:
    """Inject ConnectedValue markers into a format2 state dict for all connections.

    Walks the parameter tree to match connection paths to tool parameters,
    setting matched leaves to ``{"__class__": "ConnectedValue"}``.
    Mutates *state* in-place.

    Returns a dict of unmatched connection paths (empty if all consumed).
    """
    remaining = dict(connections)
    for tool_input in tool_inputs:
        _merge_param(remaining, tool_input, state)
    return remaining


def _merge_param(
    connections: Dict[str, object],
    tool_input: ToolParameterT,
    state: dict,
    prefix: Optional[str] = None,
    branch_connections: Optional[Dict[str, object]] = None,
):
    if branch_connections is None:
        branch_connections = connections

    name = tool_input.name
    parameter_type = tool_input.parameter_type
    state_path = flat_state_path(name, prefix)

    if parameter_type == "gx_conditional":
        conditional_state = state.get(name, {})
        if name not in state:
            state[name] = conditional_state

        conditional = cast(ConditionalParameterModel, tool_input)
        when = select_which_when_format2(conditional, conditional_state)
        conditional_connections = keys_starting_with(branch_connections, state_path)

        _merge_param(
            connections,
            conditional.test_parameter,
            conditional_state,
            prefix=state_path,
            branch_connections=conditional_connections,
        )
        if when is not None:
            for when_parameter in when.parameters:
                _merge_param(
                    connections,
                    when_parameter,
                    conditional_state,
                    prefix=state_path,
                    branch_connections=conditional_connections,
                )

    elif parameter_type == "gx_repeat":
        repeat_state_array = state.get(name, [])
        repeat = cast(RepeatParameterModel, tool_input)
        repeat_instance_connects = repeat_inputs_to_array(state_path, connections)

        for i, repeat_instance_connect in enumerate(repeat_instance_connects):
            while len(repeat_state_array) <= i:
                repeat_state_array.append({})
            instance_prefix = f"{state_path}_{i}"
            for repeat_parameter in repeat.parameters:
                _merge_param(
                    connections,
                    repeat_parameter,
                    repeat_state_array[i],
                    prefix=instance_prefix,
                    branch_connections=repeat_instance_connect,
                )

        if repeat_state_array and name not in state:
            state[name] = repeat_state_array

    elif parameter_type == "gx_section":
        section_state = state.get(name, {})
        if name not in state:
            state[name] = section_state
        section = cast(SectionParameterModel, tool_input)
        section_connections = keys_starting_with(branch_connections, state_path)
        for section_parameter in section.parameters:
            _merge_param(
                connections,
                section_parameter,
                section_state,
                prefix=state_path,
                branch_connections=section_connections,
            )

    else:
        if state_path in branch_connections:
            state[name] = {"__class__": "ConnectedValue"}
            del connections[state_path]

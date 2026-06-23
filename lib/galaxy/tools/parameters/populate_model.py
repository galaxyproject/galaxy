from typing import (
    Any,
    Optional,
)

from galaxy.util.expressions import ExpressionContext
from .basic import ImplicitConversionRequired
from .pagination import OptionsPaginationT


def populate_model(
    request_context,
    inputs,
    state_inputs,
    group_inputs: list[dict[str, Any]],
    other_values=None,
    options_pagination: Optional[OptionsPaginationT] = None,
    name_prefix: str = "",
):
    """
    Populates the tool model consumed by the client form builder.

    ``options_pagination`` maps a parameter's full dotted name (Galaxy's
    ``|``-separated convention, e.g. ``cond|input1`` or ``rep_0|input1``) to a
    per-source pagination spec, e.g. ``{"hda": {"offset": 50, "limit": 50}}``.
    Passed through to data/data_collection parameter ``to_dict`` calls.
    """
    options_pagination = options_pagination or {}
    other_values = ExpressionContext(state_inputs, other_values)
    for input_index, input in enumerate(inputs.values()):
        tool_dict = None
        group_state = state_inputs.get(input.name, {})
        full_name = f"{name_prefix}{input.name}"
        if input.type == "repeat":
            tool_dict = input.to_dict(request_context)
            group_size = len(group_state)
            tool_dict["cache"] = [None] * group_size
            group_cache: list[list[dict[str, Any]]] = tool_dict["cache"]
            for i in range(group_size):
                group_cache[i] = []
                populate_model(
                    request_context,
                    input.inputs,
                    group_state[i],
                    group_cache[i],
                    other_values,
                    options_pagination=options_pagination,
                    name_prefix=f"{full_name}_{i}|",
                )
        elif input.type == "conditional":
            tool_dict = input.to_dict(request_context)
            if "test_param" in tool_dict:
                test_param = tool_dict["test_param"]
                test_param["value"] = input.test_param.value_to_basic(
                    group_state.get(
                        test_param["name"], input.test_param.get_initial_value(request_context, other_values)
                    ),
                    request_context.app,
                )
                test_param["text_value"] = input.test_param.value_to_display_text(test_param["value"])
                for i in range(len(tool_dict["cases"])):
                    current_state = {}
                    if i == group_state.get("__current_case__"):
                        current_state = group_state
                    populate_model(
                        request_context,
                        input.cases[i].inputs,
                        current_state,
                        tool_dict["cases"][i]["inputs"],
                        other_values,
                        options_pagination=options_pagination,
                        name_prefix=f"{full_name}|",
                    )
        elif input.type == "section":
            tool_dict = input.to_dict(request_context)
            populate_model(
                request_context,
                input.inputs,
                group_state,
                tool_dict["inputs"],
                other_values,
                options_pagination=options_pagination,
                name_prefix=f"{full_name}|",
            )
        elif input.type == "upload_dataset":
            tool_dict = input.to_dict(request_context)
        else:
            pagination_spec = options_pagination.get(full_name) if input.type in ("data", "data_collection") else None
            try:
                initial_value = input.get_initial_value(request_context, other_values)
                if pagination_spec is not None:
                    tool_dict = input.to_dict(request_context, other_values=other_values, pagination=pagination_spec)
                else:
                    tool_dict = input.to_dict(request_context, other_values=other_values)
                tool_dict["value"] = input.value_to_basic(
                    state_inputs.get(input.name, initial_value), request_context.app, use_security=True
                )
                tool_dict["default_value"] = input.value_to_basic(initial_value, request_context.app, use_security=True)
                tool_dict["text_value"] = input.value_to_display_text(tool_dict["value"])
            except ImplicitConversionRequired:
                if pagination_spec is not None:
                    tool_dict = input.to_dict(request_context, other_values=other_values, pagination=pagination_spec)
                else:
                    tool_dict = input.to_dict(request_context, other_values=other_values)
                # This hack leads client to display a text field
                tool_dict["textable"] = True
        if input_index >= len(group_inputs):
            group_inputs.append(tool_dict)
        else:
            group_inputs[input_index] = tool_dict

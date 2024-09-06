import logging
from typing import (
    Any,
    Dict,
    List,
)

from galaxy.util.expressions import ExpressionContext
from .basic import ImplicitConversionRequired

log = logging.getLogger(__name__)


def populate_model(request_context, inputs, state_inputs, group_inputs: List[Dict[str, Any]], other_values=None):
    """
    Populates the tool model consumed by the client form builder.
    """
    other_values = ExpressionContext(state_inputs, other_values)
    for input_index, input in enumerate(inputs.values()):
        tool_dict = None
        group_state = state_inputs.get(input.name, {})
        if input.type == "repeat":
            tool_dict = input.to_dict(request_context)
            group_size = len(group_state)
            tool_dict["cache"] = [None] * group_size
            group_cache: List[List[str]] = tool_dict["cache"]
            for i in range(group_size):
                group_cache[i] = []
                populate_model(request_context, input.inputs, group_state[i], group_cache[i], other_values)
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
                    )
        elif input.type == "section":
            tool_dict = input.to_dict(request_context)
            populate_model(request_context, input.inputs, group_state, tool_dict["inputs"], other_values)
        else:
            try:
                initial_value = input.get_initial_value(request_context, other_values)
                tool_dict = input.to_dict(request_context, other_values=other_values)
                tool_dict["value"] = input.value_to_basic(
                    state_inputs.get(input.name, initial_value), request_context.app, use_security=True
                )
                tool_dict["default_value"] = input.value_to_basic(initial_value, request_context.app, use_security=True)
                tool_dict["text_value"] = input.value_to_display_text(tool_dict["value"])
            except ImplicitConversionRequired:
                tool_dict = input.to_dict(request_context)
                # This hack leads client to display a text field
                tool_dict["textable"] = True
            except Exception:
                tool_dict = input.to_dict(request_context)
                log.exception("tools::to_json() - Skipping parameter expansion '%s'", input.name)
        if input_index >= len(group_inputs):
            group_inputs.append(tool_dict)
        else:
            group_inputs[input_index] = tool_dict

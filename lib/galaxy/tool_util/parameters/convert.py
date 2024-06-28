"""Utilities for converting between request states.
"""

from typing import (
    Any,
    Callable,
)

from .models import (
    ToolParameterBundle,
    ToolParameterT,
)
from .state import (
    RequestInternalToolState,
    RequestToolState,
)
from .visitor import (
    visit_input_values,
    VISITOR_NO_REPLACEMENT,
)


def decode(
    external_state: RequestToolState, input_models: ToolParameterBundle, decode_id: Callable[[str], int]
) -> RequestInternalToolState:
    """Prepare an external representation of tool state (request) for storing in the database (request_internal)."""

    external_state.validate(input_models)

    def decode_callback(parameter: ToolParameterT, value: Any):
        if parameter.parameter_type == "gx_data":
            assert isinstance(value, dict), str(value)
            assert "id" in value
            decoded_dict = value.copy()
            decoded_dict["id"] = decode_id(value["id"])
            return decoded_dict
        else:
            return VISITOR_NO_REPLACEMENT

    internal_state_dict = visit_input_values(
        input_models,
        external_state,
        decode_callback,
    )

    internal_request_state = RequestInternalToolState(internal_state_dict)
    internal_request_state.validate(input_models)
    return internal_request_state


def encode(
    external_state: RequestInternalToolState, input_models: ToolParameterBundle, encode_id: Callable[[int], str]
) -> RequestToolState:
    """Prepare an external representation of tool state (request) for storing in the database (request_internal)."""

    def encode_callback(parameter: ToolParameterT, value: Any):
        if parameter.parameter_type == "gx_data":
            assert isinstance(value, dict), str(value)
            assert "id" in value
            encoded_dict = value.copy()
            encoded_dict["id"] = encode_id(value["id"])
            return encoded_dict
        else:
            return VISITOR_NO_REPLACEMENT

    request_state_dict = visit_input_values(
        input_models,
        external_state,
        encode_callback,
    )
    request_state = RequestToolState(request_state_dict)
    request_state.validate(input_models)
    return request_state

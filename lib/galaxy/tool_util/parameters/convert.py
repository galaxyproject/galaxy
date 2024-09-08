"""Utilities for converting between request states.
"""

import logging
from typing import (
    Any,
    Callable,
    cast,
    List,
)

from galaxy.tool_util.parser.interface import (
    JsonTestCollectionDefDict,
    JsonTestDatasetDefDict,
)
from .models import (
    DataCollectionRequest,
    DataParameterModel,
    DataRequest,
    SelectParameterModel,
    ToolParameterBundle,
    ToolParameterT,
)
from .state import (
    RequestInternalToolState,
    RequestToolState,
    TestCaseToolState,
)
from .visitor import (
    visit_input_values,
    VISITOR_NO_REPLACEMENT,
)

log = logging.getLogger(__name__)


def decode(
    external_state: RequestToolState, input_models: ToolParameterBundle, decode_id: Callable[[str], int]
) -> RequestInternalToolState:
    """Prepare an external representation of tool state (request) for storing in the database (request_internal)."""

    external_state.validate(input_models)

    def decode_src_dict(src_dict: dict):
        assert "id" in src_dict
        decoded_dict = src_dict.copy()
        decoded_dict["id"] = decode_id(src_dict["id"])
        return decoded_dict

    def decode_callback(parameter: ToolParameterT, value: Any):
        if parameter.parameter_type == "gx_data":
            data_parameter = cast(DataParameterModel, parameter)
            if data_parameter.multiple:
                assert isinstance(value, list), str(value)
                return list(map(decode_src_dict, value))
            else:
                assert isinstance(value, dict), str(value)
                return decode_src_dict(value)
        elif parameter.parameter_type == "gx_data_collection":
            assert isinstance(value, dict), str(value)
            return decode_src_dict(value)
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

    def encode_src_dict(src_dict: dict):
        assert "id" in src_dict
        encoded_dict = src_dict.copy()
        encoded_dict["id"] = encode_id(src_dict["id"])
        return encoded_dict

    def encode_callback(parameter: ToolParameterT, value: Any):
        if parameter.parameter_type == "gx_data":
            data_parameter = cast(DataParameterModel, parameter)
            if data_parameter.multiple:
                assert isinstance(value, list), str(value)
                return list(map(encode_src_dict, value))
            else:
                assert isinstance(value, dict), str(value)
                return encode_src_dict(value)
        elif parameter.parameter_type == "gx_data_collection":
            assert isinstance(value, dict), str(value)
            return encode_src_dict(value)
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


# interfaces for adapting test data dictionaries to tool request dictionaries
# e.g. {class: File, path: foo.bed} => {src: hda, id: ab1235cdfea3}
AdaptDatasets = Callable[[JsonTestDatasetDefDict], DataRequest]
AdaptCollections = Callable[[JsonTestCollectionDefDict], DataCollectionRequest]


def encode_test(
    test_case_state: TestCaseToolState,
    input_models: ToolParameterBundle,
    adapt_datasets: AdaptDatasets,
    adapt_collections: AdaptCollections,
):

    def encode_callback(parameter: ToolParameterT, value: Any):
        if parameter.parameter_type == "gx_data":
            data_parameter = cast(DataParameterModel, parameter)
            if value is not None:
                if data_parameter.multiple:
                    assert isinstance(value, list), str(value)
                    test_datasets = cast(List[JsonTestDatasetDefDict], value)
                    return [d.model_dump() for d in map(adapt_datasets, test_datasets)]
                else:
                    assert isinstance(value, dict), str(value)
                    test_dataset = cast(JsonTestDatasetDefDict, value)
                    return adapt_datasets(test_dataset).model_dump()
        elif parameter.parameter_type == "gx_data_collection":
            # data_collection_parameter = cast(DataCollectionParameterModel, parameter)
            if value is not None:
                assert isinstance(value, dict), str(value)
                test_collection = cast(JsonTestCollectionDefDict, value)
                return adapt_collections(test_collection).model_dump()
        elif parameter.parameter_type == "gx_select":
            select_parameter = cast(SelectParameterModel, parameter)
            if select_parameter.multiple and value is not None:
                return [v.strip() for v in value.split(",")]
            else:
                return VISITOR_NO_REPLACEMENT

        return VISITOR_NO_REPLACEMENT

    request_state_dict = visit_input_values(
        input_models,
        test_case_state,
        encode_callback,
    )
    request_state = RequestToolState(request_state_dict)
    request_state.validate(input_models)
    return request_state

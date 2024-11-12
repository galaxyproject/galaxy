"""Utilities for converting between request states.
"""

import logging
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    List,
    Optional,
    Union,
)

from galaxy.tool_util.parser.interface import (
    JsonTestCollectionDefDict,
    JsonTestDatasetDefDict,
)
from .models import (
    BooleanParameterModel,
    ConditionalParameterModel,
    ConditionalWhen,
    DataCollectionRequest,
    DataColumnParameterModel,
    DataParameterModel,
    DataRequestHda,
    DataRequestInternalHda,
    DataRequestUri,
    DiscriminatorType,
    DrillDownParameterModel,
    FloatParameterModel,
    GenomeBuildParameterModel,
    HiddenParameterModel,
    IntegerParameterModel,
    RepeatParameterModel,
    SectionParameterModel,
    SelectParameterModel,
    ToolParameterBundle,
    ToolParameterT,
)
from .state import (
    JobInternalToolState,
    LandingRequestInternalToolState,
    LandingRequestToolState,
    RequestInternalDereferencedToolState,
    RequestInternalToolState,
    RequestToolState,
    TestCaseToolState,
)
from .visitor import (
    Callback,
    validate_explicit_conditional_test_value,
    visit_input_values,
    VISITOR_NO_REPLACEMENT,
)

log = logging.getLogger(__name__)


DecodeFunctionT = Callable[[str], int]
EncodeFunctionT = Callable[[int], str]
DereferenceCallable = Callable[[DataRequestUri], DataRequestInternalHda]
# interfaces for adapting test data dictionaries to tool request dictionaries
# e.g. {class: File, path: foo.bed} => {src: hda, id: ab1235cdfea3}
AdaptDatasets = Callable[[JsonTestDatasetDefDict], DataRequestHda]
AdaptCollections = Callable[[JsonTestCollectionDefDict], DataCollectionRequest]


def decode(
    external_state: RequestToolState, input_models: ToolParameterBundle, decode_id: Callable[[str], int]
) -> RequestInternalToolState:
    """Prepare an internal representation of tool state (request_internal) for storing in the database."""

    external_state.validate(input_models)
    decode_callback = _decode_callback_for(decode_id)
    internal_state_dict = visit_input_values(
        input_models,
        external_state,
        decode_callback,
    )

    internal_request_state = RequestInternalToolState(internal_state_dict)
    internal_request_state.validate(input_models)
    return internal_request_state


def encode(
    internal_state: RequestInternalToolState, input_models: ToolParameterBundle, encode_id: EncodeFunctionT
) -> RequestToolState:
    """Prepare an external representation of tool state (request) from persisted state in the database (request_internal)."""

    encode_callback = _encode_callback_for(encode_id)
    request_state_dict = visit_input_values(
        input_models,
        internal_state,
        encode_callback,
    )
    request_state = RequestToolState(request_state_dict)
    request_state.validate(input_models)
    return request_state


def landing_decode(
    external_state: LandingRequestToolState, input_models: ToolParameterBundle, decode_id: Callable[[str], int]
) -> LandingRequestInternalToolState:
    """Prepare an external representation of tool state (request) for storing in the database (request_internal)."""

    external_state.validate(input_models)
    decode_callback = _decode_callback_for(decode_id)
    internal_state_dict = visit_input_values(
        input_models,
        external_state,
        decode_callback,
    )

    internal_request_state = LandingRequestInternalToolState(internal_state_dict)
    internal_request_state.validate(input_models)
    return internal_request_state


def landing_encode(
    internal_state: LandingRequestInternalToolState, input_models: ToolParameterBundle, encode_id: EncodeFunctionT
) -> LandingRequestToolState:
    """Prepare an external representation of tool state (request) for storing in the database (request_internal)."""

    encode_callback = _encode_callback_for(encode_id)
    request_state_dict = visit_input_values(
        input_models,
        internal_state,
        encode_callback,
    )
    request_state = LandingRequestToolState(request_state_dict)
    request_state.validate(input_models)
    return request_state


def dereference(
    internal_state: RequestInternalToolState, input_models: ToolParameterBundle, dereference: DereferenceCallable
) -> RequestInternalDereferencedToolState:

    def derefrence_dict(src_dict: dict):
        src = src_dict.get("src")
        if src == "url":
            data_request_uri: DataRequestUri = DataRequestUri.model_validate(src_dict)
            data_request_hda: DataRequestInternalHda = dereference(data_request_uri)
            return data_request_hda.model_dump()
        else:
            return src_dict

    def dereference_callback(parameter: ToolParameterT, value: Any):
        if parameter.parameter_type == "gx_data":
            if value is None:
                return VISITOR_NO_REPLACEMENT
            data_parameter = cast(DataParameterModel, parameter)
            if data_parameter.multiple:
                assert isinstance(value, list), str(value)
                return list(map(derefrence_dict, value))
            else:
                assert isinstance(value, dict), str(value)
                return derefrence_dict(value)
        else:
            return VISITOR_NO_REPLACEMENT

    request_state_dict = visit_input_values(
        input_models,
        internal_state,
        dereference_callback,
    )
    request_state = RequestInternalDereferencedToolState(request_state_dict)
    request_state.validate(input_models)
    return request_state


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
        elif parameter.parameter_type == "gx_drill_down":
            drilldown = cast(DrillDownParameterModel, parameter)
            if drilldown.multiple and value is not None:
                return [v.strip() for v in value.split(",")]
            else:
                return VISITOR_NO_REPLACEMENT
        elif parameter.parameter_type == "gx_data_column":
            data_column = cast(DataColumnParameterModel, parameter)
            is_multiple = data_column.multiple
            if is_multiple and value is not None and isinstance(value, (str,)):
                return [int(v.strip()) for v in value.split(",")]
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


def fill_static_defaults(
    tool_state: Dict[str, Any], input_models: ToolParameterBundle, profile: float, partial: bool = True
) -> Dict[str, Any]:
    """If additional defaults might stem from Galaxy runtime, partial should be true.

    Setting partial to True, prevents runtime validation.
    """
    _fill_defaults(tool_state, input_models)

    if not partial:
        internal_state = JobInternalToolState(tool_state)
        internal_state.validate(input_models)
    return tool_state


def _fill_defaults(tool_state: Dict[str, Any], input_models: ToolParameterBundle) -> None:
    for parameter in input_models.parameters:
        _fill_default_for(tool_state, parameter)


def _fill_default_for(tool_state: Dict[str, Any], parameter: ToolParameterT) -> None:
    parameter_name = parameter.name
    parameter_type = parameter.parameter_type
    if parameter_type == "gx_boolean":
        boolean = cast(BooleanParameterModel, parameter)
        if parameter_name not in tool_state:
            # even optional parameters default to false if not in the body of the request :_(
            # see test_tools.py -> expression_null_handling_boolean or test cases for gx_boolean_optional.xml
            tool_state[parameter_name] = boolean.value or False

    if parameter_type in ["gx_integer", "gx_float", "gx_hidden"]:
        has_value_parameter = cast(
            Union[
                IntegerParameterModel,
                FloatParameterModel,
                HiddenParameterModel,
            ],
            parameter,
        )
        if parameter_name not in tool_state:
            tool_state[parameter_name] = has_value_parameter.value
    elif parameter_type == "gx_genomebuild":
        genomebuild = cast(GenomeBuildParameterModel, parameter)
        if parameter_name not in tool_state and genomebuild.optional:
            tool_state[parameter_name] = None
    elif parameter_type == "gx_select":
        select = cast(SelectParameterModel, parameter)
        # don't fill in dynamic parameters - wait for runtime to specify the default
        if select.dynamic_options:
            return

        if parameter_name not in tool_state:
            if not select.multiple:
                tool_state[parameter_name] = select.default_value
            else:
                tool_state[parameter_name] = None
    elif parameter_type == "gx_drill_down":
        if parameter_name not in tool_state:
            drilldown = cast(DrillDownParameterModel, parameter)
            if drilldown.multiple:
                options = drilldown.default_options
                if options is not None:
                    tool_state[parameter_name] = options
            else:
                option = drilldown.default_option
                if option is not None:
                    tool_state[parameter_name] = option
    elif parameter_type in ["gx_conditional"]:
        if parameter_name not in tool_state:
            tool_state[parameter_name] = {}

        raw_conditional_state = tool_state[parameter_name]
        assert isinstance(raw_conditional_state, dict)
        conditional_state = cast(Dict[str, Any], raw_conditional_state)

        conditional = cast(ConditionalParameterModel, parameter)
        test_parameter = conditional.test_parameter
        test_parameter_name = test_parameter.name

        explicit_test_value: Optional[DiscriminatorType] = (
            conditional_state[test_parameter_name] if test_parameter_name in conditional_state else None
        )
        test_value = validate_explicit_conditional_test_value(test_parameter_name, explicit_test_value)
        when = _select_which_when(conditional, test_value, conditional_state)
        _fill_default_for(conditional_state, test_parameter)
        _fill_defaults(conditional_state, when)
    elif parameter_type in ["gx_repeat"]:
        if parameter_name not in tool_state:
            tool_state[parameter_name] = []
        repeat_instances = cast(List[Dict[str, Any]], tool_state[parameter_name])
        repeat = cast(RepeatParameterModel, parameter)
        if repeat.min:
            while len(repeat_instances) < repeat.min:
                repeat_instances.append({})

        for instance_state in tool_state[parameter_name]:
            _fill_defaults(instance_state, repeat)
    elif parameter_type in ["gx_section"]:
        if parameter_name not in tool_state:
            tool_state[parameter_name] = {}
        section_state = cast(Dict[str, Any], tool_state[parameter_name])
        section = cast(SectionParameterModel, parameter)
        _fill_defaults(section_state, section)


def _select_which_when(
    conditional: ConditionalParameterModel, test_value: Optional[DiscriminatorType], conditional_state: Dict[str, Any]
) -> ConditionalWhen:
    for when in conditional.whens:
        if test_value is None and when.is_default_when:
            return when
        elif test_value == when.discriminator:
            return when
    else:
        raise Exception(
            f"Invalid conditional test value ({test_value}) for parameter ({conditional.test_parameter.name})"
        )


def _encode_callback_for(encode_id: EncodeFunctionT) -> Callback:

    def encode_src_dict(src_dict: dict):
        if "id" in src_dict:
            encoded_dict = src_dict.copy()
            encoded_dict["id"] = encode_id(src_dict["id"])
            return encoded_dict
        else:
            return src_dict

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

    return encode_callback


def _decode_callback_for(decode_id: DecodeFunctionT) -> Callback:

    def decode_src_dict(src_dict: dict):
        if "id" in src_dict:
            decoded_dict = src_dict.copy()
            decoded_dict["id"] = decode_id(src_dict["id"])
            return decoded_dict
        else:
            return src_dict

    def decode_callback(parameter: ToolParameterT, value: Any):
        if parameter.parameter_type == "gx_data":
            if value is None:
                return VISITOR_NO_REPLACEMENT
            data_parameter = cast(DataParameterModel, parameter)
            if data_parameter.multiple:
                assert isinstance(value, list), str(value)
                return list(map(decode_src_dict, value))
            else:
                assert isinstance(value, dict), str(value)
                return decode_src_dict(value)
        elif parameter.parameter_type == "gx_data_collection":
            if value is None:
                return VISITOR_NO_REPLACEMENT
            assert isinstance(value, dict), str(value)
            return decode_src_dict(value)
        else:
            return VISITOR_NO_REPLACEMENT

    return decode_callback

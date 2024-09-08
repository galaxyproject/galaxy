from typing import (
    Dict,
    Optional,
)

from galaxy.tool_util.parameters import (
    DataRequestInternalHda,
    DataRequestUri,
    decode,
    dereference,
    encode,
    input_models_for_tool_source,
    RequestInternalDereferencedToolState,
    RequestInternalToolState,
    RequestToolState,
)
from .test_parameter_test_cases import tool_source_for

EXAMPLE_ID_1_ENCODED = "123456789abcde"
EXAMPLE_ID_1 = 13
EXAMPLE_ID_2_ENCODED = "123456789abcd2"
EXAMPLE_ID_2 = 14

ID_MAP: Dict[int, str] = {
    EXAMPLE_ID_1: EXAMPLE_ID_1_ENCODED,
    EXAMPLE_ID_2: EXAMPLE_ID_2_ENCODED,
}


def test_encode_data():
    tool_source = tool_source_for("parameters/gx_data")
    bundle = input_models_for_tool_source(tool_source)
    request_state = RequestToolState({"parameter": {"src": "hda", "id": EXAMPLE_ID_1_ENCODED}})
    request_state.validate(bundle)
    decoded_state = decode(request_state, bundle, _fake_decode)
    assert decoded_state.input_state["parameter"]["src"] == "hda"
    assert decoded_state.input_state["parameter"]["id"] == EXAMPLE_ID_1


def test_encode_collection():
    tool_source = tool_source_for("parameters/gx_data_collection")
    bundle = input_models_for_tool_source(tool_source)
    request_state = RequestToolState({"parameter": {"src": "hdca", "id": EXAMPLE_ID_1_ENCODED}})
    request_state.validate(bundle)
    decoded_state = decode(request_state, bundle, _fake_decode)
    assert decoded_state.input_state["parameter"]["src"] == "hdca"
    assert decoded_state.input_state["parameter"]["id"] == EXAMPLE_ID_1


def test_encode_repeat():
    tool_source = tool_source_for("parameters/gx_repeat_data")
    bundle = input_models_for_tool_source(tool_source)
    request_state = RequestToolState({"parameter": [{"data_parameter": {"src": "hda", "id": EXAMPLE_ID_1_ENCODED}}]})
    request_state.validate(bundle)
    decoded_state = decode(request_state, bundle, _fake_decode)
    assert decoded_state.input_state["parameter"][0]["data_parameter"]["src"] == "hda"
    assert decoded_state.input_state["parameter"][0]["data_parameter"]["id"] == EXAMPLE_ID_1


def test_encode_section():
    tool_source = tool_source_for("parameters/gx_section_data")
    bundle = input_models_for_tool_source(tool_source)
    request_state = RequestToolState({"parameter": {"data_parameter": {"src": "hda", "id": EXAMPLE_ID_1_ENCODED}}})
    request_state.validate(bundle)
    decoded_state = decode(request_state, bundle, _fake_decode)
    assert decoded_state.input_state["parameter"]["data_parameter"]["src"] == "hda"
    assert decoded_state.input_state["parameter"]["data_parameter"]["id"] == EXAMPLE_ID_1


def test_encode_conditional():
    tool_source = tool_source_for("identifier_in_conditional")
    bundle = input_models_for_tool_source(tool_source)
    request_state = RequestToolState(
        {"outer_cond": {"multi_input": False, "input1": {"src": "hda", "id": EXAMPLE_ID_1_ENCODED}}}
    )
    request_state.validate(bundle)
    decoded_state = decode(request_state, bundle, _fake_decode)
    assert decoded_state.input_state["outer_cond"]["input1"]["src"] == "hda"
    assert decoded_state.input_state["outer_cond"]["input1"]["id"] == EXAMPLE_ID_1


def test_multi_data():
    tool_source = tool_source_for("parameters/gx_data_multiple")
    bundle = input_models_for_tool_source(tool_source)
    request_state = RequestToolState(
        {"parameter": [{"src": "hda", "id": EXAMPLE_ID_1_ENCODED}, {"src": "hda", "id": EXAMPLE_ID_2_ENCODED}]}
    )
    request_state.validate(bundle)
    decoded_state = decode(request_state, bundle, _fake_decode)
    assert decoded_state.input_state["parameter"][0]["src"] == "hda"
    assert decoded_state.input_state["parameter"][0]["id"] == EXAMPLE_ID_1
    assert decoded_state.input_state["parameter"][1]["src"] == "hda"
    assert decoded_state.input_state["parameter"][1]["id"] == EXAMPLE_ID_2

    encoded_state = encode(decoded_state, bundle, _fake_encode)
    assert encoded_state.input_state["parameter"][0]["src"] == "hda"
    assert encoded_state.input_state["parameter"][0]["id"] == EXAMPLE_ID_1_ENCODED
    assert encoded_state.input_state["parameter"][1]["src"] == "hda"
    assert encoded_state.input_state["parameter"][1]["id"] == EXAMPLE_ID_2_ENCODED


def test_dereference():
    tool_source = tool_source_for("parameters/gx_data")
    bundle = input_models_for_tool_source(tool_source)
    raw_request_state = {"parameter": {"src": "url", "url": "gxfiles://mystorage/1.bed", "ext": "bed"}}
    request_state = RequestInternalToolState(raw_request_state)
    request_state.validate(bundle)

    exception: Optional[Exception] = None
    try:
        # quickly verify this request needs to be dereferenced
        bad_state = RequestInternalDereferencedToolState(raw_request_state)
        bad_state.validate(bundle)
    except Exception as e:
        exception = e
    assert exception is not None

    dereferenced_state = dereference(request_state, bundle, _fake_dereference)
    assert isinstance(dereferenced_state, RequestInternalDereferencedToolState)
    dereferenced_state.validate(bundle)


def _fake_dereference(input: DataRequestUri) -> DataRequestInternalHda:
    return DataRequestInternalHda(id=EXAMPLE_ID_1)


def _fake_decode(input: str) -> int:
    return next(key for key, value in ID_MAP.items() if value == input)


def _fake_encode(input: int) -> str:
    return ID_MAP[input]

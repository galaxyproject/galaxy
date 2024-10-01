from typing import (
    Any,
    Dict,
    Optional,
)

from galaxy.tool_util.parameters import (
    DataRequestInternalHda,
    DataRequestUri,
    decode,
    dereference,
    encode,
    fill_static_defaults,
    input_models_for_tool_source,
    RequestInternalDereferencedToolState,
    RequestInternalToolState,
    RequestToolState,
)
from galaxy.tool_util.parser.util import parse_profile_version
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


def test_fill_defaults():
    with_defaults = fill_state_for({}, "parameters/gx_int")
    assert with_defaults["parameter"] == 1
    with_defaults = fill_state_for({}, "parameters/gx_float")
    assert with_defaults["parameter"] == 1.0
    with_defaults = fill_state_for({}, "parameters/gx_boolean")
    assert with_defaults["parameter"] is False
    with_defaults = fill_state_for({}, "parameters/gx_boolean_optional")
    # This is False unfortunately - see comments in gx_boolean_optional XML.
    assert with_defaults["parameter"] is False
    with_defaults = fill_state_for({}, "parameters/gx_boolean_checked")
    assert with_defaults["parameter"] is True
    with_defaults = fill_state_for({}, "parameters/gx_boolean_optional_checked")
    assert with_defaults["parameter"] is True

    with_defaults = fill_state_for({}, "parameters/gx_conditional_boolean")
    assert with_defaults["conditional_parameter"]["test_parameter"] is False
    assert with_defaults["conditional_parameter"]["boolean_parameter"] is False

    with_defaults = fill_state_for({"conditional_parameter": {}}, "parameters/gx_conditional_boolean")
    assert with_defaults["conditional_parameter"]["test_parameter"] is False
    assert with_defaults["conditional_parameter"]["boolean_parameter"] is False

    with_defaults = fill_state_for({}, "parameters/gx_repeat_boolean")
    assert len(with_defaults["parameter"]) == 0
    with_defaults = fill_state_for({"parameter": [{}]}, "parameters/gx_repeat_boolean")
    assert len(with_defaults["parameter"]) == 1
    instance_state = with_defaults["parameter"][0]
    assert instance_state["boolean_parameter"] is False

    with_defaults = fill_state_for({}, "parameters/gx_repeat_boolean_min")
    assert len(with_defaults["parameter"]) == 2
    assert with_defaults["parameter"][0]["boolean_parameter"] is False
    assert with_defaults["parameter"][1]["boolean_parameter"] is False
    with_defaults = fill_state_for({"parameter": [{}, {}]}, "parameters/gx_repeat_boolean_min")
    assert len(with_defaults["parameter"]) == 2
    assert with_defaults["parameter"][0]["boolean_parameter"] is False
    assert with_defaults["parameter"][1]["boolean_parameter"] is False
    with_defaults = fill_state_for({"parameter": [{}]}, "parameters/gx_repeat_boolean_min")
    assert with_defaults["parameter"][0]["boolean_parameter"] is False
    assert with_defaults["parameter"][1]["boolean_parameter"] is False

    with_defaults = fill_state_for({}, "parameters/gx_section_boolean")
    assert with_defaults["parameter"]["boolean_parameter"] is False

    with_defaults = fill_state_for({}, "parameters/gx_drill_down_exact_with_selection")
    assert with_defaults["parameter"] == "aba"

    with_defaults = fill_state_for({}, "parameters/gx_hidden")
    assert with_defaults["parameter"] == "moo"

    with_defaults = fill_state_for({}, "parameters/gx_genomebuild_optional")
    assert with_defaults["parameter"] is None

    with_defaults = fill_state_for({}, "parameters/gx_select")
    assert with_defaults["parameter"] == "--ex1"

    with_defaults = fill_state_for({}, "parameters/gx_select_optional")
    assert with_defaults["parameter"] is None

    # Not ideal but matching current behavior
    with_defaults = fill_state_for({}, "parameters/gx_select_multiple")
    assert with_defaults["parameter"] is None

    with_defaults = fill_state_for({}, "parameters/gx_select_multiple_optional")
    assert with_defaults["parameter"] is None

    # Do not fill in dynamic defaults... these require a Galaxy runtime.
    with_defaults = fill_state_for({}, "remove_value", partial=True)
    assert "choose_value" not in with_defaults

    with_defaults = fill_state_for(
        {"single": {"src": "hda", "id": 4}}, "select_from_dataset_in_conditional", partial=True
    )
    assert with_defaults["cond"]["cond"] == "single"
    assert with_defaults["cond"]["inner_cond"]["inner_cond"] == "single"


def _fake_dereference(input: DataRequestUri) -> DataRequestInternalHda:
    return DataRequestInternalHda(id=EXAMPLE_ID_1)


def _fake_decode(input: str) -> int:
    return next(key for key, value in ID_MAP.items() if value == input)


def _fake_encode(input: int) -> str:
    return ID_MAP[input]


def fill_state_for(tool_state: Dict[str, Any], tool_path: str, partial: bool = False) -> Dict[str, Any]:
    tool_source = tool_source_for(tool_path)
    bundle = input_models_for_tool_source(tool_source)
    profile = parse_profile_version(tool_source)
    internal_state = fill_static_defaults(tool_state, bundle, profile, partial=partial)
    return internal_state

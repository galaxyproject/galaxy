from functools import partial
from typing import (
    Any,
    Callable,
    Dict,
    List,
)

import yaml

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.tool_util.parameters import (
    decode,
    encode,
    RequestInternalToolState,
    RequestToolState,
    ToolParameterModel,
    validate_internal_job,
    validate_internal_request,
    validate_request,
    validate_test_case,
)
from galaxy.tool_util.parameters.json import to_json_schema_string
from galaxy.tool_util.unittest_utils.parameters import (
    parameter_bundle,
    parameter_bundle_for_file,
    tool_parameter,
)
from galaxy.util.resources import resource_string


def specification_object():
    try:
        yaml_str = resource_string(__package__, "parameter_specification.yml")
    except AttributeError:
        # hack for the main() function below where this file is interpreted as part of the
        # Galaxy tree.
        yaml_str = open("test/unit/tool_util/parameter_specification.yml").read()
    return yaml.safe_load(yaml_str)


def test_specification():
    parameter_spec = specification_object()
    for file in parameter_spec.keys():
        _test_file(file, parameter_spec)


def test_single():
    # _test_file("gx_int")
    # _test_file("gx_float")
    # _test_file("gx_boolean")
    # _test_file("gx_int_optional")
    # _test_file("gx_float_optional")
    # _test_file("gx_conditional_boolean")
    # _test_file("gx_conditional_conditional_boolean")
    _test_file("gx_conditional_boolean_checked")


def _test_file(file: str, specification=None):
    spec = specification or specification_object()
    combos = spec[file]
    tool_parameter_model = tool_parameter(file)
    for valid_or_invalid, tests in combos.items():
        if valid_or_invalid == "request_valid":
            _assert_requests_validate(tool_parameter_model, tests)
        elif valid_or_invalid == "request_invalid":
            _assert_requests_invalid(tool_parameter_model, tests)
        elif valid_or_invalid == "request_internal_valid":
            _assert_internal_requests_validate(tool_parameter_model, tests)
        elif valid_or_invalid == "request_internal_invalid":
            _assert_internal_requests_invalid(tool_parameter_model, tests)
        elif valid_or_invalid == "job_internal_valid":
            _assert_internal_jobs_validate(tool_parameter_model, tests)
        elif valid_or_invalid == "job_internal_invalid":
            _assert_internal_jobs_invalid(tool_parameter_model, tests)
        elif valid_or_invalid == "test_case_valid":
            _assert_test_cases_validate(tool_parameter_model, tests)
        elif valid_or_invalid == "test_case_invalid":
            _assert_test_cases_invalid(tool_parameter_model, tests)

    # Assume request validation will work here.
    if "request_internal_valid" not in combos and "request_valid" in combos:
        _assert_internal_requests_validate(tool_parameter_model, combos["request_valid"])
    if "request_internal_invalid" not in combos and "request_invalid" in combos:
        _assert_internal_requests_invalid(tool_parameter_model, combos["request_invalid"])


def _for_each(test: Callable, parameter: ToolParameterModel, requests: List[Dict[str, Any]]) -> None:
    for request in requests:
        test(parameter, request)


def _assert_request_validates(parameter, request) -> None:
    try:
        validate_request(parameter_bundle(parameter), request)
    except RequestParameterInvalidException as e:
        raise AssertionError(f"Parameter {parameter} failed to validate request {request}. {e}")


def _assert_request_invalid(parameter, request) -> None:
    exc = None
    try:
        validate_request(parameter_bundle(parameter), request)
    except RequestParameterInvalidException as e:
        exc = e
    assert exc is not None, f"Parameter {parameter} didn't result in validation error on request {request} as expected."


def _assert_internal_request_validates(parameter, request) -> None:
    try:
        validate_internal_request(parameter_bundle(parameter), request)
    except RequestParameterInvalidException as e:
        raise AssertionError(f"Parameter {parameter} failed to validate internal request {request}. {e}")


def _assert_internal_request_invalid(parameter, request) -> None:
    exc = None
    try:
        validate_internal_request(parameter_bundle(parameter), request)
    except RequestParameterInvalidException as e:
        exc = e
    assert (
        exc is not None
    ), f"Parameter {parameter} didn't result in validation error on internal request {request} as expected."


def _assert_internal_job_validates(parameter, request) -> None:
    try:
        validate_internal_job(parameter_bundle(parameter), request)
    except RequestParameterInvalidException as e:
        raise AssertionError(f"Parameter {parameter} failed to validate internal job description {request}. {e}")


def _assert_internal_job_invalid(parameter, request) -> None:
    exc = None
    try:
        validate_internal_job(parameter_bundle(parameter), request)
    except RequestParameterInvalidException as e:
        exc = e
    assert (
        exc is not None
    ), f"Parameter {parameter} didn't result in validation error on internal job description {request} as expected."


def _assert_test_case_validates(parameter, test_case) -> None:
    try:
        validate_test_case(parameter_bundle(parameter), test_case)
    except RequestParameterInvalidException as e:
        raise AssertionError(f"Parameter {parameter} failed to validate test_case {test_case}. {e}")


def _assert_test_case_invalid(parameter, test_case) -> None:
    exc = None
    try:
        validate_test_case(parameter_bundle(parameter), test_case)
    except RequestParameterInvalidException as e:
        exc = e
    assert (
        exc is not None
    ), f"Parameter {parameter} didn't result in validation error on test_case {test_case} as expected."


_assert_requests_validate = partial(_for_each, _assert_request_validates)
_assert_requests_invalid = partial(_for_each, _assert_request_invalid)
_assert_internal_requests_validate = partial(_for_each, _assert_internal_request_validates)
_assert_internal_requests_invalid = partial(_for_each, _assert_internal_request_invalid)
_assert_internal_jobs_validate = partial(_for_each, _assert_internal_job_validates)
_assert_internal_jobs_invalid = partial(_for_each, _assert_internal_job_invalid)
_assert_test_cases_validate = partial(_for_each, _assert_test_case_validates)
_assert_test_cases_invalid = partial(_for_each, _assert_test_case_invalid)


def decode_val(val: str) -> int:
    assert val == "abcdabcd"
    return 5


def test_decode_gx_data():
    input_bundle = parameter_bundle_for_file("gx_data")

    request_tool_state = RequestToolState({"parameter": {"src": "hda", "id": "abcdabcd"}})
    request_internal_tool_state = decode(request_tool_state, input_bundle, decode_val)
    assert request_internal_tool_state.input_state["parameter"]["id"] == 5
    assert request_internal_tool_state.input_state["parameter"]["src"] == "hda"


def test_decode_gx_int():
    input_bundle = parameter_bundle_for_file("gx_int")

    request_tool_state = RequestToolState({"parameter": 5})
    request_internal_tool_state = decode(request_tool_state, input_bundle, decode_val)
    assert request_internal_tool_state.input_state["parameter"] == 5


def test_json_schema_for_conditional():
    input_bundle = parameter_bundle_for_file("gx_conditional_boolean")
    tool_state = RequestToolState.parameter_model_for(input_bundle)
    print(to_json_schema_string(tool_state))


def test_encode_gx_data():
    input_bundle = parameter_bundle_for_file("gx_data")

    def encode_val(val: int) -> str:
        assert val == 5
        return "abcdabcd"

    request_internal_tool_state = RequestInternalToolState({"parameter": {"src": "hda", "id": 5}})
    request_tool_state = encode(request_internal_tool_state, input_bundle, encode_val)
    assert request_tool_state.input_state["parameter"]["id"] == "abcdabcd"
    assert request_tool_state.input_state["parameter"]["src"] == "hda"


if __name__ == "__main__":
    parameter_spec = specification_object()
    parameter_models_json = {}
    for file in parameter_spec.keys():
        tool_parameter_model = tool_parameter(file)
        parameter_models_json[file] = tool_parameter_model.dict()
    yaml_str = yaml.safe_dump(parameter_models_json)
    with open("client/src/components/Tool/parameter_models.yml", "w") as f:
        f.write("# auto generated file for JavaScript testing, do not modify manually\n")
        f.write("# -----\n")
        f.write('# PYTHONPATH="lib" python test/unit/tool_util/test_parameter_specification.py\n')
        f.write("# -----\n")
        f.write(yaml_str)

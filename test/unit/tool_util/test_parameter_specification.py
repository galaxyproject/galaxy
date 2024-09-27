import sys
from functools import partial
from typing import (
    Callable,
    List,
    Optional,
)

import pytest
import yaml

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.tool_util.parameters import (
    decode,
    encode,
    RawStateDict,
    RequestInternalToolState,
    RequestToolState,
    ToolParameterBundleModel,
    validate_internal_job,
    validate_internal_landing_request,
    validate_internal_request,
    validate_internal_request_dereferenced,
    validate_landing_request,
    validate_request,
    validate_test_case,
    validate_workflow_step,
    validate_workflow_step_linked,
    ValidationFunctionT,
)
from galaxy.tool_util.parameters.json import to_json_schema_string
from galaxy.tool_util.unittest_utils.parameters import (
    parameter_bundle_for_file,
    parameter_bundle_for_framework_tool,
)
from galaxy.util.resources import resource_string

if sys.version_info < (3, 8):  # noqa: UP036
    pytest.skip(reason="Pydantic tool parameter models require python3.8 or higher", allow_module_level=True)


def specification_object():
    try:
        yaml_str = resource_string(__package__, "parameter_specification.yml")
    except AttributeError:
        # hack for the main() function below where this file is interpreted as part of the
        # Galaxy tree.
        yaml_str = open("test/unit/tool_util/parameter_specification.yml").read()
    return yaml.safe_load(yaml_str)


def framework_tool_checks():
    # Extend parameter_specification with some extra tests against existing framework tools.
    # There is something beautiful about a targeted tool for every parameter feature but realistically
    # we've been doing a version of the for a decade with tool tests and we can leverage those also.
    try:
        yaml_str = resource_string(__package__, "framework_tool_checks.yml")
    except AttributeError:
        # hack for the main() function below where this file is interpreted as part of the
        # Galaxy tree.
        yaml_str = open("test/unit/tool_util/framework_tool_checks.yml").read()
    return yaml.safe_load(yaml_str)


def test_specification():
    parameter_spec = specification_object()
    for file in parameter_spec.keys():
        _test_file(file, parameter_spec)


def test_framework_tool_checks():
    parameter_spec = framework_tool_checks()
    for file in parameter_spec.keys():
        _test_file(file, parameter_spec, parameter_bundle_for_framework_tool(f"{file}.xml"))


def test_single():
    # _test_file("gx_int")
    # _test_file("gx_float")
    # _test_file("gx_boolean")
    # _test_file("gx_int_optional")
    # _test_file("gx_float_optional")
    # _test_file("gx_conditional_boolean")
    # _test_file("gx_conditional_conditional_boolean")
    _test_file("gx_conditional_boolean_checked")


def _test_file(file: str, specification=None, parameter_bundle: Optional[ToolParameterBundleModel] = None):
    spec = specification or specification_object()
    combos = spec[file]
    if parameter_bundle is None:
        parameter_bundle = parameter_bundle_for_file(file)
    assert parameter_bundle

    assertion_functions = {
        "request_valid": _assert_requests_validate,
        "request_invalid": _assert_requests_invalid,
        "request_internal_valid": _assert_internal_requests_validate,
        "request_internal_invalid": _assert_internal_requests_invalid,
        "request_internal_dereferenced_valid": _assert_internal_requests_dereferenced_validate,
        "request_internal_dereferenced_invalid": _assert_internal_requests_dereferenced_invalid,
        "landing_request_valid": _assert_landing_requests_validate,
        "landing_request_invalid": _assert_landing_requests_invalid,
        "landing_request_internal_valid": _assert_internal_landing_requests_validate,
        "landing_request_internal_invalid": _assert_internal_landing_requests_invalid,
        "job_internal_valid": _assert_internal_jobs_validate,
        "job_internal_invalid": _assert_internal_jobs_invalid,
        "test_case_xml_valid": _assert_test_cases_validate,
        "test_case_xml_invalid": _assert_test_cases_invalid,
        "workflow_step_valid": _assert_workflow_steps_validate,
        "workflow_step_invalid": _assert_workflow_steps_invalid,
        "workflow_step_linked_valid": _assert_workflow_steps_linked_validate,
        "workflow_step_linked_invalid": _assert_workflow_steps_linked_invalid,
    }

    for valid_or_invalid, tests in combos.items():
        assertion_function = assertion_functions[valid_or_invalid]
        assertion_function(parameter_bundle, tests)

    # Assume request validation will work here.
    if "request_internal_valid" not in combos and "request_valid" in combos:
        _assert_internal_requests_validate(parameter_bundle, combos["request_valid"])
    if "request_internal_invalid" not in combos and "request_invalid" in combos:
        _assert_internal_requests_invalid(parameter_bundle, combos["request_invalid"])


def _for_each(test: Callable, parameters: ToolParameterBundleModel, requests: List[RawStateDict]) -> None:
    for request in requests:
        test(parameters, request)


def model_assertion_function_factory(validate_function: ValidationFunctionT, what: str):

    def _assert_validates(parameters: ToolParameterBundleModel, request: RawStateDict) -> None:
        try:
            validate_function(parameters, request)
        except RequestParameterInvalidException as e:
            raise AssertionError(f"Parameters {parameters} failed to validate {what} {request}. {e}")

    def _assert_invalid(parameters: ToolParameterBundleModel, request: RawStateDict) -> None:
        exc = None
        try:
            validate_function(parameters, request)
        except RequestParameterInvalidException as e:
            exc = e

        if exc is None:
            raise AssertionError(
                f"Parameters {parameters} didn't result in validation error on {what} {request} as expected."
            )

    return _assert_validates, _assert_invalid


_assert_request_validates, _assert_request_invalid = model_assertion_function_factory(validate_request, "request")
_assert_internal_request_validates, _assert_internal_request_invalid = model_assertion_function_factory(
    validate_internal_request, "internal request"
)
_assert_internal_request_dereferenced_validates, _assert_internal_request_dereferenced_invalid = (
    model_assertion_function_factory(validate_internal_request_dereferenced, "dereferenced internal request")
)
_assert_internal_job_validates, _assert_internal_job_invalid = model_assertion_function_factory(
    validate_internal_job, "internal job description"
)
_assert_test_case_validates, _assert_test_case_invalid = model_assertion_function_factory(
    validate_test_case, "XML derived test case"
)
_assert_workflow_step_validates, _assert_workflow_step_invalid = model_assertion_function_factory(
    validate_workflow_step, "workflow step tool state (unlinked)"
)
_assert_workflow_step_linked_validates, _assert_workflow_step_linked_invalid = model_assertion_function_factory(
    validate_workflow_step_linked, "linked workflow step tool state"
)
_assert_landing_request_validates, _assert_landing_request_invalid = model_assertion_function_factory(
    validate_landing_request, "landing request"
)
_assert_internal_landing_request_validates, _assert_internal_landing_request_invalid = model_assertion_function_factory(
    validate_internal_landing_request, " internallanding request"
)

_assert_requests_validate = partial(_for_each, _assert_request_validates)
_assert_requests_invalid = partial(_for_each, _assert_request_invalid)
_assert_internal_requests_validate = partial(_for_each, _assert_internal_request_validates)
_assert_internal_requests_invalid = partial(_for_each, _assert_internal_request_invalid)
_assert_internal_requests_dereferenced_validate = partial(_for_each, _assert_internal_request_dereferenced_validates)
_assert_internal_requests_dereferenced_invalid = partial(_for_each, _assert_internal_request_dereferenced_invalid)
_assert_internal_jobs_validate = partial(_for_each, _assert_internal_job_validates)
_assert_internal_jobs_invalid = partial(_for_each, _assert_internal_job_invalid)
_assert_test_cases_validate = partial(_for_each, _assert_test_case_validates)
_assert_test_cases_invalid = partial(_for_each, _assert_test_case_invalid)
_assert_workflow_steps_validate = partial(_for_each, _assert_workflow_step_validates)
_assert_workflow_steps_invalid = partial(_for_each, _assert_workflow_step_invalid)
_assert_workflow_steps_linked_validate = partial(_for_each, _assert_workflow_step_linked_validates)
_assert_workflow_steps_linked_invalid = partial(_for_each, _assert_workflow_step_linked_invalid)
_assert_landing_requests_validate = partial(_for_each, _assert_landing_request_validates)
_assert_landing_requests_invalid = partial(_for_each, _assert_landing_request_invalid)
_assert_internal_landing_requests_validate = partial(_for_each, _assert_internal_landing_request_validates)
_assert_internal_landing_requests_invalid = partial(_for_each, _assert_internal_landing_request_invalid)


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
        tool_parameter_model = parameter_bundle_for_file(file)
        parameter_models_json[file] = tool_parameter_model.dict()
    yaml_str = yaml.safe_dump(parameter_models_json)
    with open("client/src/components/Tool/parameter_models.yml", "w") as f:
        f.write("# auto generated file for JavaScript testing, do not modify manually\n")
        f.write("# -----\n")
        f.write('# PYTHONPATH="lib" python test/unit/tool_util/test_parameter_specification.py\n')
        f.write("# -----\n")
        f.write(yaml_str)

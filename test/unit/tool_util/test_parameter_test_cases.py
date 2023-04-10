from typing import List

from galaxy.tool_util.parameters.case import test_case_state as case_state
from galaxy.tool_util.unittest_utils.parameters import (
    parameter_bundle_for_file,
    parameter_tool_source,
)


def test_parameter_test_cases_validate():
    validate_test_cases_for("gx_int")
    warnings = validate_test_cases_for("gx_float")
    assert len(warnings[0]) == 0
    assert len(warnings[1]) == 1


def validate_test_cases_for(tool_name: str) -> List[List[str]]:
    tool_parameter_bundle = parameter_bundle_for_file(tool_name)
    tool_source = parameter_tool_source(tool_name)
    profile = tool_source.parse_profile()
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    warnings_by_test = []
    for test_case in test_cases:
        test_case_state_and_warnings = case_state(test_case, tool_parameter_bundle, profile)
        tool_state = test_case_state_and_warnings.tool_state
        warnings = test_case_state_and_warnings.warnings
        assert tool_state.state_representation == "test_case"
        warnings_by_test.append(warnings)
    return warnings_by_test

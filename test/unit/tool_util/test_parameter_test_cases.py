import os
import re
import sys
from typing import List

import pytest

from galaxy.tool_util.models import parse_tool
from galaxy.tool_util.parameters.case import (
    test_case_state as case_state,
    TestCaseStateValidationResult,
    validate_test_cases_for_tool_source,
)
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.parser.interface import ToolSourceTest
from galaxy.tool_util.unittest_utils import functional_test_tool_directory
from galaxy.tool_util.verify.parse import parse_tool_test_descriptions

# legacy tools allows specifying parameter and repeat parameters without
# qualification. This was problematic and could result in ambigious specifications.
TOOLS_THAT_USE_UNQUALIFIED_PARAMETER_ACCESS = [
    "boolean_conditional.xml",
    "simple_constructs.xml",
    "section.xml",
    "collection_paired_conditional_structured_like.xml",
    "output_action_change_format.xml",
    "top_level_data.xml",
    "disambiguate_cond.xml",
    "multi_repeats.xml",
    "implicit_default_conds.xml",
    "min_repeat.xml",
]

# tools that use truevalue/falsevalue in parameter setting, I think we're going to
# forbid this for a future tool profile version. Potential ambigouity could result.
TOOLS_THAT_USE_TRUE_FALSE_VALUE_BOOLEAN_SPECIFICATION = [
    "inputs_as_json_profile.xml",
    "inputs_as_json_with_paths.xml",
    "inputs_as_json.xml",
]

TOOLS_THAT_USE_SELECT_BY_VALUE = [
    "multi_select.xml",
]


TEST_TOOL_THAT_DO_NOT_VALIDATE = (
    TOOLS_THAT_USE_UNQUALIFIED_PARAMETER_ACCESS
    + TOOLS_THAT_USE_TRUE_FALSE_VALUE_BOOLEAN_SPECIFICATION
    + TOOLS_THAT_USE_SELECT_BY_VALUE
    + [
        # will never handle upload_dataset
        "upload.xml",
    ]
)


if sys.version_info < (3, 8):  # noqa: UP036
    pytest.skip(reason="Pydantic tool parameter models require python3.8 or higher", allow_module_level=True)


def test_parameter_test_cases_validate():
    validation_result = validate_test_cases_for("column_param")
    assert len(validation_result[0].warnings) == 0
    assert len(validation_result[1].warnings) == 0
    assert len(validation_result[2].warnings) == 1

    validation_result = validate_test_cases_for("column_param", use_latest_profile=True)
    assert validation_result[2].validation_error


def test_legacy_features_fail_validation_with_24_2(tmp_path):
    for filename in TOOLS_THAT_USE_UNQUALIFIED_PARAMETER_ACCESS + TOOLS_THAT_USE_TRUE_FALSE_VALUE_BOOLEAN_SPECIFICATION:
        _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, filename)

    # column parameters need to be indexes
    _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, "column_param.xml", index=2)

    # selection by value only
    _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, "multi_select.xml", index=1)


def _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, filename: str, index: int = 0):
    test_tool_directory = functional_test_tool_directory()
    original_path = os.path.join(test_tool_directory, filename)
    new_path = tmp_path / filename
    with open(original_path) as rf:
        tool_contents = rf.read()
        tool_contents = re.sub(r'profile="[\d\.]*"', r"", tool_contents)
        new_profile_contents = tool_contents.replace("<tool ", '<tool profile="24.2" ', 1)
    with open(new_path, "w") as wf:
        wf.write(new_profile_contents)
    test_cases = list(parse_tool_test_descriptions(get_tool_source(original_path)))
    assert test_cases[index].to_dict()["error"] is False
    test_cases = list(parse_tool_test_descriptions(get_tool_source(new_path)))
    assert (
        test_cases[index].to_dict()["error"] is True
    ), f"expected {filename} to have validation failure preventing loading of tools"


def test_validate_framework_test_tools():
    test_tool_directory = functional_test_tool_directory()
    for tool_name in os.listdir(test_tool_directory):
        if tool_name in TEST_TOOL_THAT_DO_NOT_VALIDATE:
            continue
        if tool_name.endswith("_conf.xml"):
            # tool conf (toolbox) files or sample datatypes
            continue
        tool_path = os.path.join(test_tool_directory, tool_name)
        if not tool_path.endswith(".xml") or os.path.isdir(tool_path):
            continue

        try:
            _validate_path(tool_path)
        except Exception as e:
            raise Exception(f"Failed to validate {tool_path}: {str(e)}")


def _validate_path(tool_path: str):
    tool_source = get_tool_source(tool_path)
    parsed_tool = parse_tool(tool_source)
    profile = tool_source.parse_profile()
    test_cases: List[ToolSourceTest] = tool_source.parse_tests_to_dict()["tests"]
    for test_case in test_cases:
        if test_case.get("expect_failure"):
            continue
        test_case_state_and_warnings = case_state(test_case, parsed_tool.inputs, profile)
        tool_state = test_case_state_and_warnings.tool_state
        assert tool_state.state_representation == "test_case_xml"


def validate_test_cases_for(tool_name: str, **kwd) -> List[TestCaseStateValidationResult]:
    test_tool_directory = functional_test_tool_directory()
    tool_path = os.path.join(test_tool_directory, f"{tool_name}.xml")
    tool_source = get_tool_source(tool_path)
    return validate_test_cases_for_tool_source(tool_source, **kwd)

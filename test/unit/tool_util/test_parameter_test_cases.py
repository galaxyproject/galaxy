import os
import re
import sys
from typing import (
    List,
    Optional,
)

import pytest

from galaxy.tool_util.models import parse_tool
from galaxy.tool_util.parameters.case import (
    test_case_state as case_state,
    TestCaseStateAndWarnings,
    TestCaseStateValidationResult,
    validate_test_cases_for_tool_source,
)
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.parser.interface import (
    ToolSource,
    ToolSourceTest,
)
from galaxy.tool_util.unittest_utils import functional_test_tool_directory
from galaxy.tool_util.verify.parse import parse_tool_test_descriptions
from .util import dict_verify_each

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
        _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, filename, index=None)

    # column parameters need to be indexes
    _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, "column_param.xml", index=2)

    # selection by value only
    _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, "multi_select.xml", index=1)


def _assert_tool_test_parsing_only_fails_with_newer_profile(tmp_path, filename: str, index: Optional[int] = 0):
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
    if index is not None:
        assert test_cases[index].to_dict()["error"] is False
    else:
        # just make sure there is at least one failure...
        assert not any(c.to_dict()["error"] is True for c in test_cases)

    test_cases = list(parse_tool_test_descriptions(get_tool_source(new_path)))
    if index is not None:
        assert (
            test_cases[index].to_dict()["error"] is True
        ), f"expected {filename} to have validation failure preventing loading of tools"
    else:
        assert any(c.to_dict()["error"] is True for c in test_cases)


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


def test_test_case_state_conversion():
    tool_source = tool_source_for("collection_nested_test")
    test_cases: List[ToolSourceTest] = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["f1", "collection_type"], "list:paired"),
        (["f1", "class"], "Collection"),
        (["f1", "elements", 0, "class"], "Collection"),
        (["f1", "elements", 0, "collection_type"], "paired"),
        (["f1", "elements", 0, "elements", 0, "class"], "File"),
        (["f1", "elements", 0, "elements", 0, "path"], "simple_line.txt"),
        (["f1", "elements", 0, "elements", 0, "identifier"], "forward"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("dbkey_filter_input")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["inputs", "class"], "File"),
        (["inputs", "dbkey"], "hg19"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("discover_metadata_files")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["input_bam", "class"], "File"),
        (["input_bam", "filetype"], "bam"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("remote_test_data_location")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["input", "class"], "File"),
        (
            ["input", "location"],
            "https://raw.githubusercontent.com/galaxyproject/planemo/7be1bf5b3971a43eaa73f483125bfb8cabf1c440/tests/data/hello.txt",
        ),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("composite")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["input", "class"], "File"),
        (["input", "filetype"], "velvet"),
        (["input", "composite_data", 0], "velveth_test1/Sequences"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)

    tool_source = tool_source_for("parameters/gx_group_tag")
    test_cases = tool_source.parse_tests_to_dict()["tests"]
    state = case_state_for(tool_source, test_cases[0])
    expectations = [
        (["ref_parameter", "class"], "Collection"),
        (["ref_parameter", "collection_type"], "paired"),
        (["ref_parameter", "elements", 0, "identifier"], "forward"),
        (["ref_parameter", "elements", 0, "tags", 0], "group:type:single"),
    ]
    dict_verify_each(state.tool_state.input_state, expectations)


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
    return validate_test_cases_for_tool_source(tool_source_for(tool_name), **kwd)


def case_state_for(tool_source: ToolSource, test_case: ToolSourceTest) -> TestCaseStateAndWarnings:
    parsed_tool = parse_tool(tool_source)
    profile = tool_source.parse_profile()
    return case_state(test_case, parsed_tool.inputs, profile)


def tool_source_for(tool_name: str) -> ToolSource:
    test_tool_directory = functional_test_tool_directory()
    tool_path = os.path.join(test_tool_directory, f"{tool_name}.xml")
    tool_source = get_tool_source(tool_path)
    return tool_source

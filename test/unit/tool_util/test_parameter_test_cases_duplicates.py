import re
from dataclasses import dataclass
from typing import (
    Any,
    List,
)

import pytest

from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.parameters.case import (
    test_case_state as case_state,
    validate_test_cases_for_tool_source,
)
from galaxy.tool_util.parser.interface import ToolSource
from galaxy.tool_util.verify.parse import parse_tool_test_descriptions
from .test_parameter_test_cases import raw_xml_tool_source
from .util import dict_verify_each

DUPLICATE_DATA_TOOL_TEMPLATE = """
<tool id="duplicate_data" name="duplicate_data" version="1.0.0" profile="25.1">
    <command>echo</command>
    <inputs>
        <param name="input" type="data" format="txt" />
    </inputs>
    <outputs />
    <tests>
        <test>
            <param name="input" value="simple_line.txt">{first}</param>
            <param name="input" value="simple_line.txt">{second}</param>
        </test>
    </tests>
</tool>
"""


@pytest.mark.parametrize(
    "children",
    [
        '<edit_attributes type="name" value="renamed" />',
        '<composite_data value="simple_line.txt" />',
    ],
    ids=["edit_attributes", "composite_data"],
)
def test_duplicate_identical_data_test_param_with_children_is_tolerated(children):
    tool_source = raw_xml_tool_source(DUPLICATE_DATA_TOOL_TEMPLATE.format(first=children, second=children))
    [test_description] = parse_tool_test_descriptions(tool_source)
    assert not test_description.error, test_description.exception


DUPLICATE_QUALIFIED_TOOL_TEMPLATE = """
<tool id="duplicate_qualified" name="duplicate_qualified" version="1.0.0" profile="{profile}">
    <command>echo</command>
    <inputs>
        <param name="top" type="text" value="" />
        <repeat name="plain" title="Plain">
            <param name="a" type="text" value="" />
        </repeat>
        <repeat name="nested" title="Nested">
            <conditional name="source">
                <param name="selector" type="select">
                    <option value="user" selected="true">User</option>
                    <option value="other">Other</option>
                </param>
                <when value="user">
                    <param name="a" type="text" value="" />
                </when>
                <when value="other" />
            </conditional>
        </repeat>
    </inputs>
    <outputs />
    <tests>
        <test>
            {body}
        </test>
    </tests>
</tool>
"""


@dataclass
class DuplicateQualifiedPlacement:
    """A test body giving one param twice (``{first}``/``{second}``) and that param's state path."""

    body: str
    state_path: List[Any]
    flat_name: str


DUPLICATE_QUALIFIED_PLACEMENTS = {
    "top_level": DuplicateQualifiedPlacement(
        body='<param name="top" value="{first}" /><param name="top" value="{second}" />',
        state_path=["top"],
        flat_name="top",
    ),
    "repeat": DuplicateQualifiedPlacement(
        body='<repeat name="plain"><param name="a" value="{first}" /><param name="a" value="{second}" /></repeat>',
        state_path=["plain", 0, "a"],
        flat_name="plain_0|a",
    ),
    "repeat_conditional": DuplicateQualifiedPlacement(
        body='<repeat name="nested"><conditional name="source">'
        '<param name="selector" value="user" /><param name="a" value="{first}" />'
        '<param name="selector" value="user" /><param name="a" value="{second}" />'
        "</conditional></repeat>",
        state_path=["nested", 0, "source", "a"],
        flat_name="nested_0|source|a",
    ),
}


def _duplicate_qualified_tool_source(
    placement: DuplicateQualifiedPlacement, first: str, second: str, profile: str = "25.1"
) -> ToolSource:
    body = placement.body.format(first=first, second=second)
    return raw_xml_tool_source(DUPLICATE_QUALIFIED_TOOL_TEMPLATE.format(profile=profile, body=body))


@pytest.mark.parametrize(
    "placement", DUPLICATE_QUALIFIED_PLACEMENTS.values(), ids=DUPLICATE_QUALIFIED_PLACEMENTS.keys()
)
def test_duplicate_identical_qualified_test_param_is_tolerated(placement):
    tool_source = _duplicate_qualified_tool_source(placement, "A1", "A1")
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]
    tool_state = case_state(test_case, parsed_tool.inputs, tool_source.parse_profile()).tool_state
    dict_verify_each(tool_state.input_state, [(placement.state_path, "A1")])


@pytest.mark.parametrize(
    "placement", DUPLICATE_QUALIFIED_PLACEMENTS.values(), ids=DUPLICATE_QUALIFIED_PLACEMENTS.keys()
)
def test_duplicate_conflicting_qualified_test_param_is_rejected(placement):
    tool_source = _duplicate_qualified_tool_source(placement, "A1", "A2")
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]
    expected_error = f"Ambiguous test parameter ({placement.flat_name})"
    with pytest.raises(Exception, match=re.escape(expected_error)):
        case_state(test_case, parsed_tool.inputs, tool_source.parse_profile())

    [lint_result] = validate_test_cases_for_tool_source(tool_source)
    assert expected_error in str(lint_result.validation_error)

    [test_description] = parse_tool_test_descriptions(tool_source)
    assert test_description.error
    assert expected_error in str(test_description.exception)


@pytest.mark.parametrize(
    "placement", DUPLICATE_QUALIFIED_PLACEMENTS.values(), ids=DUPLICATE_QUALIFIED_PLACEMENTS.keys()
)
def test_duplicate_conflicting_qualified_test_param_legacy_profile_still_runs(placement):
    # Below 24.2 the test still runs through the legacy inputs; only the lint flags it.
    tool_source = _duplicate_qualified_tool_source(placement, "A1", "A2", profile="23.0")
    [test_description] = parse_tool_test_descriptions(tool_source)
    assert not test_description.error
    assert test_description.request is None
    assert f"Ambiguous test parameter ({placement.flat_name})" in str(test_description.request_unavailable_reason)
    assert test_description.inputs[placement.flat_name] == "A2"


def test_duplicate_data_test_param_with_conflicting_edit_attributes_is_rejected():
    tool_source = raw_xml_tool_source(
        DUPLICATE_DATA_TOOL_TEMPLATE.format(
            first='<edit_attributes type="name" value="first" />',
            second='<edit_attributes type="name" value="second" />',
        )
    )
    [test_description] = parse_tool_test_descriptions(tool_source)
    assert test_description.error
    assert "Ambiguous test parameter (input)" in str(test_description.exception)

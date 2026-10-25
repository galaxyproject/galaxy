from dataclasses import dataclass
from typing import (
    Any,
    List,
)

import pytest

from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.parameters.case import (
    test_case_state as case_state,
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
<tool id="duplicate_qualified" name="duplicate_qualified" version="1.0.0" profile="25.1">
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


DUPLICATE_QUALIFIED_PLACEMENTS = {
    "top_level": DuplicateQualifiedPlacement(
        body='<param name="top" value="{first}" /><param name="top" value="{second}" />',
        state_path=["top"],
    ),
    "repeat": DuplicateQualifiedPlacement(
        body='<repeat name="plain"><param name="a" value="{first}" /><param name="a" value="{second}" /></repeat>',
        state_path=["plain", 0, "a"],
    ),
    "repeat_conditional": DuplicateQualifiedPlacement(
        body='<repeat name="nested"><conditional name="source">'
        '<param name="selector" value="user" /><param name="a" value="{first}" />'
        '<param name="selector" value="user" /><param name="a" value="{second}" />'
        "</conditional></repeat>",
        state_path=["nested", 0, "source", "a"],
    ),
}


def _duplicate_qualified_tool_source(placement: DuplicateQualifiedPlacement, first: str, second: str) -> ToolSource:
    body = placement.body.format(first=first, second=second)
    return raw_xml_tool_source(DUPLICATE_QUALIFIED_TOOL_TEMPLATE.format(body=body))


@pytest.mark.parametrize(
    "placement", DUPLICATE_QUALIFIED_PLACEMENTS.values(), ids=DUPLICATE_QUALIFIED_PLACEMENTS.keys()
)
def test_duplicate_identical_qualified_test_param_is_tolerated(placement):
    tool_source = _duplicate_qualified_tool_source(placement, "A1", "A1")
    parsed_tool = parse_tool(tool_source)
    test_case = tool_source.parse_tests_to_dict()["tests"][0]
    tool_state = case_state(test_case, parsed_tool.inputs, tool_source.parse_profile()).tool_state
    dict_verify_each(tool_state.input_state, [(placement.state_path, "A1")])

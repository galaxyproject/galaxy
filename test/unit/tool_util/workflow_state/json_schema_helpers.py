"""Shared test helpers for JSON Schema validation tests."""

from galaxy.tool_util_models import ParsedTool
from galaxy.tool_util_models.parameters import (
    BooleanParameterModel,
    FloatParameterModel,
    IntegerParameterModel,
    SelectParameterModel,
    TextParameterModel,
)


def make_parsed_tool_rich():
    """ParsedTool with 5 param types: text, integer, float, boolean, select."""
    return ParsedTool(
        id="test_tool",
        version="1.0",
        name="Test Tool",
        description="A tool for testing",
        inputs=[
            TextParameterModel(name="input_text", parameter_type="gx_text", type="text"),
            IntegerParameterModel(name="num_lines", parameter_type="gx_integer", value="10", type="integer"),
            FloatParameterModel(name="threshold", parameter_type="gx_float", value="0.5", type="float"),
            BooleanParameterModel(
                name="header",
                parameter_type="gx_boolean",
                value="false",
                truevalue="--header",
                falsevalue="",
                type="boolean",
            ),
            SelectParameterModel(
                name="method",
                parameter_type="gx_select",
                type="select",
                options=[
                    {"label": "Mean", "value": "mean", "selected": True},
                    {"label": "Median", "value": "median", "selected": False},
                ],
            ),
        ],
        outputs=[],
        citations=[],
        license=None,
        profile=None,
        edam_operations=[],
        edam_topics=[],
        xrefs=[],
        help=None,
    )


def make_parsed_tool_simple():
    """ParsedTool with 2 param types: text, integer."""
    return ParsedTool(
        id="test_tool",
        version="1.0",
        name="Test Tool",
        description=None,
        inputs=[
            TextParameterModel(name="input_text", parameter_type="gx_text", type="text"),
            IntegerParameterModel(name="num_lines", parameter_type="gx_integer", value="10", type="integer"),
        ],
        outputs=[],
        citations=[],
        license=None,
        profile=None,
        edam_operations=[],
        edam_topics=[],
        xrefs=[],
        help=None,
    )


class FakeGetToolInfo:
    """GetToolInfo implementation that returns a single test tool."""

    def __init__(self, parsed_tool=None):
        self._tool = parsed_tool or make_parsed_tool_rich()

    def get_tool_info(self, tool_id: str, tool_version: str | None) -> ParsedTool | None:
        if tool_id == "test_tool":
            return self._tool
        return None

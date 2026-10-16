"""Converter leaf decision-table coverage for RuntimeValue / ConnectedValue markers.

Exercises ``_convert_valid_state_to_format2`` directly so each row of the decision
table is asserted in isolation (state + ``in`` block), independent of the surrounding
native/format2 validation.
"""

from galaxy.tool_util.parameters import (
    DataParameterModel,
    IntegerParameterModel,
)
from galaxy.tool_util.workflow_state.convert import _convert_valid_state_to_format2
from galaxy.tool_util_models import ParsedTool

CONNECTION = {"id": 0, "output_name": "out"}


def make_parsed_tool(inputs):
    return ParsedTool(
        id="test_tool",
        version="1.0",
        name="test_tool",
        description=None,
        license=None,
        profile=None,
        help=None,
        inputs=inputs,
        outputs=[],
        citations=[],
        edam_operations=[],
        edam_topics=[],
        xrefs=[],
    )


def make_data_input(name="input1", optional=False):
    return DataParameterModel(
        name=name,
        parameter_type="gx_data",
        type="data",
        extensions=["data"],
        multiple=False,
        hidden=False,
        optional=optional,
        is_dynamic=False,
    )


def make_tool_step(tool_id="t", input_connections=None, tool_state=None):
    step = {"type": "tool", "tool_id": tool_id}
    if input_connections:
        step["input_connections"] = input_connections
    if tool_state:
        step["tool_state"] = tool_state
    return step


def _convert(parsed_tool, tool_state, input_connections=None):
    step = make_tool_step("t", input_connections=input_connections, tool_state=tool_state)
    return _convert_valid_state_to_format2(step, parsed_tool)


def test_optional_disconnected_runtime_value_omitted():
    """Optional + disconnected RuntimeValue → emit nothing (no state key, no in entry)."""
    tool = make_parsed_tool(inputs=[make_data_input(name="names", optional=True)])
    result = _convert(tool, {"names": {"__class__": "RuntimeValue"}})
    assert "names" not in result.state
    assert "names" not in result.inputs


def test_required_disconnected_runtime_value_kept_as_placeholder():
    """Required + disconnected RuntimeValue → keep the in placeholder."""
    tool = make_parsed_tool(inputs=[make_data_input(name="names", optional=False)])
    result = _convert(tool, {"names": {"__class__": "RuntimeValue"}})
    assert result.inputs["names"] == "placeholder"
    assert "names" not in result.state


def test_connected_value_records_placeholder():
    """ConnectedValue marker → connection placeholder, never in state."""
    tool = make_parsed_tool(inputs=[make_data_input(name="names", optional=True)])
    result = _convert(
        tool,
        {"names": {"__class__": "ConnectedValue"}},
        input_connections={"names": CONNECTION},
    )
    assert result.inputs["names"] == "placeholder"
    assert "names" not in result.state


def test_legacy_connected_runtime_value_treated_as_connection():
    """Connected path carrying a RuntimeValue marker → connection wins (placeholder),
    not runtime-omitted and not double-stamped."""
    tool = make_parsed_tool(inputs=[make_data_input(name="names", optional=True)])
    result = _convert(
        tool,
        {"names": {"__class__": "RuntimeValue"}},
        input_connections={"names": CONNECTION},
    )
    assert result.inputs["names"] == "placeholder"
    assert "names" not in result.state


def test_optional_disconnected_scalar_runtime_value_omitted():
    """Optional + disconnected RuntimeValue on a scalar leaf → omitted, mirroring data."""
    num = IntegerParameterModel(name="num", parameter_type="gx_integer", type="integer", optional=True)
    tool = make_parsed_tool(inputs=[num])
    result = _convert(tool, {"num": {"__class__": "RuntimeValue"}})
    assert "num" not in result.state
    assert "num" not in result.inputs

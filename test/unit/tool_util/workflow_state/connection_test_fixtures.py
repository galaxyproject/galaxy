"""Shared test fixtures for workflow connection validation tests."""

from typing import Optional

from galaxy.tool_util.parameters import (
    DataCollectionParameterModel,
    DataParameterModel,
)
from galaxy.tool_util_models import ParsedTool
from galaxy.tool_util_models.tool_outputs import (
    ToolOutputCollection,
    ToolOutputDataset,
    ToolOutputText,
)


def make_parsed_tool(tool_id="test_tool", inputs=None, outputs=None):
    return ParsedTool(
        id=tool_id,
        version="1.0",
        name=tool_id,
        description=None,
        license=None,
        profile=None,
        help=None,
        inputs=inputs or [],
        outputs=outputs or [],
        citations=[],
        edam_operations=[],
        edam_topics=[],
        xrefs=[],
    )


def make_data_input(name="input1", extensions=None, multiple=False, optional=False):
    return DataParameterModel(
        name=name,
        parameter_type="gx_data",
        type="data",
        extensions=extensions or ["data"],
        multiple=multiple,
        hidden=False,
        optional=optional,
        is_dynamic=False,
    )


def make_collection_input(name="input1", collection_type="list", optional=False):
    return DataCollectionParameterModel(
        name=name,
        parameter_type="gx_data_collection",
        type="data_collection",
        collection_type=collection_type,
        extensions=["data"],
        hidden=False,
        optional=optional,
        is_dynamic=False,
        value=None,
    )


def make_data_output(name="out1", format="data"):
    return ToolOutputDataset(name=name, type="data", format=format, hidden=False)


def make_parameter_output(name="out1", param_type="text"):
    return ToolOutputText(name=name, type=param_type, hidden=False)


def make_collection_output(name="out1", collection_type=None, collection_type_source=None, structured_like=None):
    return ToolOutputCollection(
        name=name,
        type="collection",
        hidden=False,
        collection_type=collection_type,
        collection_type_source=collection_type_source,
        structured_like=structured_like,
    )


class MockGetToolInfo:
    """Mock GetToolInfo that returns pre-registered ParsedTools."""

    def __init__(self, tools=None):
        self._tools = tools or {}

    def register(self, tool_id, parsed_tool):
        self._tools[tool_id] = parsed_tool

    def get_tool_info(self, tool_id: str, tool_version: Optional[str]) -> Optional[ParsedTool]:
        return self._tools.get(tool_id)


def make_native_workflow(*steps):
    """Build a minimal native workflow dict from step defs."""
    return {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {str(i): s for i, s in enumerate(steps)},
    }


def make_tool_step(tool_id, input_connections=None, tool_state=None):
    step = {"type": "tool", "tool_id": tool_id}
    if input_connections:
        step["input_connections"] = input_connections
    if tool_state:
        step["tool_state"] = tool_state
    return step


def make_input_step(step_type="data_input", tool_state=None):
    step = {"type": step_type}
    if tool_state:
        step["tool_state"] = tool_state
    return step


def make_subworkflow_step(inner_workflow, input_connections=None):
    """Build a subworkflow step dict.

    input_connections entries should include input_subworkflow_step_id, e.g.:
      {"input1": {"id": 0, "output_name": "output", "input_subworkflow_step_id": 0}}
    """
    step = {
        "type": "subworkflow",
        "subworkflow": inner_workflow,
    }
    if input_connections:
        step["input_connections"] = input_connections
    return step

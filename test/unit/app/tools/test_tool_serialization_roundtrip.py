import json

from galaxy.app_unittest_utils.tools_support import mock_app_for_tool_support
from galaxy.tool_util.unittest_utils import (
    functional_test_tool_path,
    functional_test_tool_source,
)
from galaxy.tools import (
    create_tool_from_representation,
    RawToolSource,
    Tool,
)


def test_serialization_yaml():
    tool = simple_constructs_tool()
    raw = tool.to_raw_tool_source()

    assert isinstance(raw, RawToolSource)
    tool_source_json = json.loads(raw.raw_tool_source)
    assert tool_source_json
    assert tool_source_json["id"] == "simple_constructs_y"
    assert raw.tool_source_class == "YamlToolSource"


def test_repopulate_after_serialization_yaml():
    tool = simple_constructs_tool()
    raw_tool_source, tool_source_class = tool.to_raw_tool_source()

    app = mock_app_for_tool_support()
    create_tool_from_representation(
        app,
        raw_tool_source,
        tool.tool_dir,
        tool_source_class,
    )


def simple_constructs_tool() -> Tool:
    tool_path = functional_test_tool_path("simple_constructs.yml")
    tool_source = functional_test_tool_source("simple_constructs_y")

    app = mock_app_for_tool_support()
    guid = None
    tool = Tool(
        tool_path,
        tool_source,
        app,
        guid,
    )
    return tool

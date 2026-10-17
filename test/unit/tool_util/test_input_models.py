from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.tool_util_models.parameters import (
    DataCollectionParameterModel,
    DrillDownParameterModel,
)


def test_input_collection_type():
    tool_source = get_tool_source(functional_test_tool_path("parameters/gx_data_collection_list.xml"))
    tool = parse_tool(tool_source)
    tool_input = tool.inputs[0]
    assert isinstance(tool_input, DataCollectionParameterModel)
    assert tool_input.collection_type == "list"


DRILL_DOWN_FROM_FILE_TOOL = """<tool id="drill_down_from_file" name="drill_down_from_file" version="1.0.0">
    <command>echo '$parameter'</command>
    <inputs>
        <param name="parameter" type="drill_down" from_file="{from_file}" />
    </inputs>
    <outputs/>
</tool>
"""


def test_drill_down_from_file_is_not_read(tmp_path):
    options_file = tmp_path / "options.xml"
    options_file.write_text('<options><option name="Option 1" value="option1"/></options>')
    for from_file in [str(options_file), str(tmp_path / "missing.xml"), "../options.xml"]:
        tool_path = tmp_path / "tool.xml"
        tool_path.write_text(DRILL_DOWN_FROM_FILE_TOOL.format(from_file=from_file))
        tool_input = parse_tool(get_tool_source(str(tool_path))).inputs[0]
        assert isinstance(tool_input, DrillDownParameterModel)
        assert tool_input.options is None

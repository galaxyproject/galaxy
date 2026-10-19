from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.tool_util_models.parameters import (
    DataCollectionParameterModel,
    DrillDownParameterModel,
    TextParameterModel,
)
from galaxy.tool_util_models.untrusted import loading_untrusted_tools


def test_input_collection_type():
    tool_source = get_tool_source(functional_test_tool_path("parameters/gx_data_collection_list.xml"))
    tool = parse_tool(tool_source)
    tool_input = tool.inputs[0]
    assert isinstance(tool_input, DataCollectionParameterModel)
    assert tool_input.collection_type == "list"


def _parameter_model(tool_file: str):
    tool_source = get_tool_source(functional_test_tool_path(f"parameters/{tool_file}"))
    return parse_tool(tool_source).inputs[0]


def test_multiple_selects_are_optional_by_default():
    # galaxy.xsd documents this: optional "Defaults to false except when the type attribute
    # value is select and multiple is true".
    assert _parameter_model("gx_select_multiple.xml").optional is True
    assert _parameter_model("gx_select.xml").optional is False


def test_multiple_genomebuilds_are_optional_by_default():
    # GenomeBuildParameter subclasses SelectToolParameter, so it inherits the same rule.
    assert _parameter_model("gx_genomebuild_multiple.xml").optional is True
    assert _parameter_model("gx_genomebuild.xml").optional is False
    assert _parameter_model("gx_genomebuild_optional.xml").optional is True


def test_drill_down_optional_attribute_is_parsed():
    # multiple does not imply optional here - DrillDownSelectToolParameter goes through
    # ToolParameter.__init__, which reads a bare parse_optional().
    assert _parameter_model("gx_drill_down_exact_optional.xml").optional is True
    assert _parameter_model("gx_drill_down_exact.xml").optional is False
    assert _parameter_model("gx_drill_down_exact_multiple.xml").optional is False


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


EXPRESSION_VALIDATOR_TOOL = """<tool id="expression_validator" name="expression_validator" version="1.0.0">
    <command>echo '$parameter'</command>
    <inputs>
        <param name="parameter" type="text">
            <validator type="expression">__import__('pathlib').Path('{marker}').touch() is None</validator>
        </param>
    </inputs>
    <outputs/>
</tool>
"""


def test_untrusted_expression_validator_is_not_evaluated(tmp_path):
    marker = tmp_path / "marker"
    tool_path = tmp_path / "tool.xml"
    tool_path.write_text(EXPRESSION_VALIDATOR_TOOL.format(marker=marker))
    with loading_untrusted_tools():
        untrusted_input = parse_tool(get_tool_source(str(tool_path))).inputs[0]
    assert not marker.exists()
    assert isinstance(untrusted_input, TextParameterModel)
    assert untrusted_input.optional is False
    # trusted tools still infer optionality from their validators
    trusted_input = parse_tool(get_tool_source(str(tool_path))).inputs[0]
    assert marker.exists()
    assert isinstance(trusted_input, TextParameterModel)
    assert trusted_input.optional is True

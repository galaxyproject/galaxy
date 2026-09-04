from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.tool_util_models.parameters import DataCollectionParameterModel


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

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

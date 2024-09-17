from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.parser.output_models import from_tool_source
from galaxy.tool_util.unittest_utils import functional_test_tool_path


def test_from_tool_data_table():
    tool_source = get_tool_source(functional_test_tool_path("dbkey_output_action.xml"))
    # prevent regression of https://github.com/galaxyproject/galaxy/issues/18554. Tool fails without fix
    from_tool_source(tool_source)

from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.parser.output_objects import from_tool_source
from galaxy.tool_util.unittest_utils import functional_test_tool_path


def test_from_tool_data_table():
    tool_source = get_tool_source(functional_test_tool_path("dbkey_output_action.xml"))
    # prevent regression of https://github.com/galaxyproject/galaxy/issues/18554. Tool fails without fix
    from_tool_source(tool_source)


def test_xml_parser_keeps_output_filters():
    tool_source = get_tool_source(functional_test_tool_path("output_filter.xml"))
    outputs, _ = tool_source.parse_outputs(None)
    assert [f.text for f in outputs["out_1"].filters] == ["produce_out_1 is True"]
    assert [f.text for f in outputs["out_2"].filters] == [
        'filter_text_1 in ["foo", "bar"]',
        'filter_text_1 == "foo"',
    ]
    assert [f.text for f in outputs["list_output"].filters] == ["produce_collection is True"]

from galaxy.workflow.gx_validator import GET_TOOL_INFO


def test_get_tool():
    parsed_tool = GET_TOOL_INFO.get_tool_info("cat1", "1.0.0")
    assert parsed_tool
    assert parsed_tool.id == "cat1"
    assert parsed_tool.version == "1.0.0"

    parsed_tool = GET_TOOL_INFO.get_tool_info("cat1", None)
    assert parsed_tool
    assert parsed_tool.id == "cat1"
    assert parsed_tool.version == "1.0.0"

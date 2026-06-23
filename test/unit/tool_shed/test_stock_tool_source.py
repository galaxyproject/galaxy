from tool_shed.managers.tools import _stock_tool_source_for


def test_serves_workflow_safe_version_on_exact_miss():
    # sort1 only ships 1.2.0; 1.1.0 is within its safe-update range and resolves to it.
    tool_source = _stock_tool_source_for("sort1", "1.1.0")
    assert tool_source is not None
    assert tool_source.parse_version() == "1.2.0"


def test_returns_none_for_out_of_range_version():
    assert _stock_tool_source_for("sort1", "0.0.1") is None

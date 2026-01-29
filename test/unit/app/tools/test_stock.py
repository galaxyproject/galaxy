from galaxy.tools.stock import (
    stock_tool_paths,
    stock_tool_sources,
)


def test_stock_tool_paths():
    file_names = [f.name for f in list(stock_tool_paths())]
    assert "merge_collection.xml" in file_names
    assert "meme.xml" in file_names
    assert "output_auto_format.xml" in file_names


def test_stock_tool_sources():
    tool_source = next(stock_tool_sources())
    assert tool_source.parse_id()

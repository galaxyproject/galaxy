"""Pin ``build_index_entry_from_source`` metadata capture."""

from datetime import (
    datetime,
    timezone,
)

from galaxy.tool_util.parser import get_tool_source
from galaxy.tools.source_store.discover import (
    CONVERTER_TOOL_CONF,
    DiscoveredTool,
)
from galaxy.tools.source_store.interface import StoredToolSource
from galaxy.tools.source_store.populator import (
    build_index_entry_from_source,
    MAX_HELP_TEXT_CHARS,
)

_TOOL_XML = """<tool id="help_tool" name="Help Tool" version="1.0">
  <command>echo</command>
  <inputs/>
  <outputs/>
  <help>This wraps the quaxifier subroutine.</help>
</tool>
"""

_TOOL_XML_NO_HELP = """<tool id="plain_tool" name="Plain Tool" version="1.0">
  <command>echo</command>
  <inputs/>
  <outputs/>
</tool>
"""


def _stored(path, tool_source):
    return StoredToolSource(
        hash="deadbeef",
        tool_source_class=type(tool_source).__name__,
        raw_source=tool_source.to_string(),
        tool_id=tool_source.parse_id(),
        tool_version=tool_source.parse_version(),
        tool_dir=str(path.parent),
        source_path=str(path),
        stored_at=datetime.now(timezone.utc),
        metadata={},
    )


def _build(tmp_path, xml, tool_conf="tool_conf.xml"):
    path = tmp_path / "tool.xml"
    path.write_text(xml)
    tool_source = get_tool_source(config_file=str(path))
    discovered = DiscoveredTool(path=str(path), tool_conf=tool_conf, tool_path=str(tmp_path))
    return build_index_entry_from_source(discovered, _stored(path, tool_source), tool_source)


def test_entry_marks_datatype_converter(tmp_path):
    plain = _build(tmp_path, _TOOL_XML)
    converter = _build(tmp_path, _TOOL_XML, tool_conf=CONVERTER_TOOL_CONF)
    assert plain is not None and plain.is_datatype_converter is False
    assert converter is not None and converter.is_datatype_converter is True


def test_entry_captures_help_text(tmp_path):
    entry = _build(tmp_path, _TOOL_XML)
    assert entry is not None
    assert "quaxifier" in entry.help_text


def test_entry_help_text_empty_without_help_block(tmp_path):
    entry = _build(tmp_path, _TOOL_XML_NO_HELP)
    assert entry is not None
    assert entry.help_text == ""


def test_entry_help_text_capped(tmp_path):
    huge = "quaxifier " * (MAX_HELP_TEXT_CHARS // 2)
    xml = _TOOL_XML.replace("This wraps the quaxifier subroutine.", huge)
    entry = _build(tmp_path, xml)
    assert entry is not None
    assert len(entry.help_text) <= MAX_HELP_TEXT_CHARS

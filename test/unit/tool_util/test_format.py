from galaxy.tool_util.format import (
    format_xml,
    main,
)

SIMPLE_TOOL_XML = """\
<tool id="test" name="Test" version="1.0">
<description>A test tool</description>
<command>echo hello</command>
<inputs>
<param name="input1" type="data" format="txt"/>
</inputs>
<outputs>
<data name="output1" format="txt"/>
</outputs>
</tool>"""

EXPECTED_FORMATTED = """\
<tool id="test" name="Test" version="1.0">
    <description>A test tool</description>
    <command>echo hello</command>
    <inputs>
        <param name="input1" type="data" format="txt"/>
    </inputs>
    <outputs>
        <data name="output1" format="txt"/>
    </outputs>
</tool>
"""

CDATA_XML = """\
<tool id="test" name="Test" version="1.0">
<command><![CDATA[echo "hello world"]]></command>
</tool>"""

COMMENT_XML = """\
<tool id="test" name="Test" version="1.0">
<!-- This is a comment -->
<command>echo hello</command>
</tool>"""


def test_basic_formatting():
    result = format_xml(SIMPLE_TOOL_XML)
    assert result == EXPECTED_FORMATTED


def test_tab_size_2():
    result = format_xml(SIMPLE_TOOL_XML, tab_size=2)
    assert "  <description>" in result
    assert "    <param" in result


def test_cdata_preserved():
    result = format_xml(CDATA_XML)
    assert "CDATA" in result
    assert 'echo "hello world"' in result


def test_comments_preserved():
    result = format_xml(COMMENT_XML)
    assert "<!-- This is a comment -->" in result


def test_invalid_xml_returned_unchanged():
    bad_xml = "<tool><unclosed>"
    result = format_xml(bad_xml)
    assert result == bad_xml


def test_idempotent():
    first = format_xml(SIMPLE_TOOL_XML)
    second = format_xml(first)
    assert first == second


def test_cli_inplace(tmp_path):
    tool_file = tmp_path / "tool.xml"
    tool_file.write_text(SIMPLE_TOOL_XML)
    main([str(tool_file)])
    assert tool_file.read_text() == EXPECTED_FORMATTED


def test_cli_already_formatted(tmp_path, capsys):
    tool_file = tmp_path / "tool.xml"
    tool_file.write_text(EXPECTED_FORMATTED)
    main([str(tool_file)])
    assert tool_file.read_text() == EXPECTED_FORMATTED
    assert "already formatted" in capsys.readouterr().out


def test_cli_diff_mode(tmp_path, capsys):
    tool_file = tmp_path / "tool.xml"
    tool_file.write_text(SIMPLE_TOOL_XML)
    try:
        main(["--diff", str(tool_file)])
    except SystemExit as e:
        assert e.code == 1
    # file should be unchanged in diff mode
    assert tool_file.read_text() == SIMPLE_TOOL_XML
    assert "---" in capsys.readouterr().out


def test_cli_diff_mode_no_changes(tmp_path):
    tool_file = tmp_path / "tool.xml"
    tool_file.write_text(EXPECTED_FORMATTED)
    # should not raise SystemExit
    main(["--diff", str(tool_file)])


def test_cli_tab_size(tmp_path):
    tool_file = tmp_path / "tool.xml"
    tool_file.write_text(SIMPLE_TOOL_XML)
    main(["--tab-size", "2", str(tool_file)])
    result = tool_file.read_text()
    assert "  <description>" in result
    assert "    <param" in result


def test_cli_multiple_files(tmp_path):
    f1 = tmp_path / "tool1.xml"
    f2 = tmp_path / "tool2.xml"
    f1.write_text(SIMPLE_TOOL_XML)
    f2.write_text(SIMPLE_TOOL_XML)
    main([str(f1), str(f2)])
    assert f1.read_text() == EXPECTED_FORMATTED
    assert f2.read_text() == EXPECTED_FORMATTED


def test_cli_invalid_xml_unchanged(tmp_path):
    bad_xml = "<tool><unclosed>"
    tool_file = tmp_path / "tool.xml"
    tool_file.write_text(bad_xml)
    main([str(tool_file)])
    assert tool_file.read_text() == bad_xml

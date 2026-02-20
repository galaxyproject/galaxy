from galaxy.tool_util.format import format_xml

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

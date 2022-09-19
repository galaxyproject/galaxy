import errno
import tempfile
from io import StringIO
from typing import Dict

import pytest

from galaxy import util
from galaxy.util.json import safe_loads

SECTION_XML = """<?xml version="1.0" ?>
<section id="fasta_fastq_manipulation" name="Fasta Fastq Manipulation" version="">
    <tool file="toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/fb1313d79396/seq_filter_by_id/tools/seq_filter_by_id/seq_filter_by_id.xml" guid="toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/seq_filter_by_id/0.2.5">
        <tool_shed>
            toolshed.g2.bx.psu.edu
        </tool_shed>
    </tool>
</section>
"""


def test_strip_control_characters():
    s = "\x00bla"
    assert util.strip_control_characters(s) == "bla"


def test_parse_xml_string():
    section = util.parse_xml_string(SECTION_XML)
    _verify_section(section)


def test_parse_xml_file():
    with tempfile.NamedTemporaryFile(mode="w") as tmp:
        tmp.write(SECTION_XML)
        tmp.flush()
        section = util.parse_xml(tmp.name).getroot()
    _verify_section(section)


def _verify_section(section):
    tool = next(iter(section))
    assert sorted(tool.items()) == [
        (
            "file",
            "toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/fb1313d79396/seq_filter_by_id/tools/seq_filter_by_id/seq_filter_by_id.xml",
        ),
        ("guid", "toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/seq_filter_by_id/0.2.5"),
    ]
    assert next(iter(tool)).text == "toolshed.g2.bx.psu.edu"


def test_xml_to_string():
    section = util.parse_xml_string(SECTION_XML)
    s = util.xml_to_string(section)
    assert len(s.split("\n")) == 1


def test_xml_to_string_pretty():
    section = util.parse_xml_string(SECTION_XML)
    s = util.xml_to_string(section, pretty=True)
    PRETTY = """<?xml version="1.0" ?>
<section id="fasta_fastq_manipulation" name="Fasta Fastq Manipulation" version="">
    <tool file="toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/fb1313d79396/seq_filter_by_id/tools/seq_filter_by_id/seq_filter_by_id.xml" guid="toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/seq_filter_by_id/0.2.5">
        <tool_shed>toolshed.g2.bx.psu.edu</tool_shed>
    </tool>
</section>"""
    assert s == PRETTY


def test_parse_xml_enoent():
    with tempfile.NamedTemporaryFile() as temp:
        path = temp.name
    with pytest.raises(IOError) as excinfo:
        util.parse_xml(path)
    assert excinfo.value.errno == errno.ENOENT


def test_clean_multiline_string():
    x = util.clean_multiline_string(
        """
        a
        b
        c
"""
    )
    assert x == "a\nb\nc\n"


def test_iter_start_of_lines():
    assert list(util.iter_start_of_line(StringIO("\n1\n\n12\n123\n1234\n"), 1)) == ["\n", "1", "\n", "1", "1", "1"]


def test_safe_loads():
    d: Dict[str, str] = {}
    rval = safe_loads(d)
    assert rval == d
    assert rval is not d
    rval["foo"] = "bar"
    assert "foo" not in d
    s = '{"foo": "bar"}'
    assert safe_loads(s) == {"foo": "bar"}

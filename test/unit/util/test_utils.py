from tempfile import NamedTemporaryFile

from galaxy import util

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
    s = '\x00bla'
    assert util.strip_control_characters(s) == 'bla'


def test_strip_control_characters_nested():
    s = '\x00bla'
    stripped_s = 'bla'
    l = [s]
    t = (s, 'blub')
    d = {42: s}
    assert util.strip_control_characters_nested(l)[0] == stripped_s
    assert util.strip_control_characters_nested(t)[0] == stripped_s
    assert util.strip_control_characters_nested(d)[42] == stripped_s


def test_parse_xml_string():
    section = util.parse_xml_string(SECTION_XML)
    _verify_section(section)


def test_parse_xml_file():
    with NamedTemporaryFile(mode='w') as tmp:
        tmp.write(SECTION_XML)
        tmp.flush()
        section = util.parse_xml(tmp.name).getroot()
    _verify_section(section)


def _verify_section(section):
    tool = next(iter(section))
    assert sorted(tool.items()) == [
        ('file',
         'toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/fb1313d79396/seq_filter_by_id/tools/seq_filter_by_id/seq_filter_by_id.xml'),
        ('guid',
         'toolshed.g2.bx.psu.edu/repos/peterjc/seq_filter_by_id/seq_filter_by_id/0.2.5')
    ]
    assert next(iter(tool)).text == 'toolshed.g2.bx.psu.edu'


def test_xml_to_string():
    section = util.parse_xml_string(SECTION_XML)
    s = util.xml_to_string(section)
    assert len(s.split('\n')) == 1


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

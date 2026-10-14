from galaxy.tool_util.toolbox import ToolSection
from galaxy.util import etree


def test_tool_section():
    elem = etree.Element("section")
    elem.attrib["name"] = "Cool Tools"
    elem.attrib["id"] = "cool1"

    section = ToolSection(elem)
    assert section.id == "cool1"
    assert section.name == "Cool Tools"
    assert section.version == ""

    section = ToolSection(dict(id="cool1", name="Cool Tools"))
    assert section.id == "cool1"
    assert section.name == "Cool Tools"
    assert section.version == ""

    section = ToolSection()
    assert section.id == ""
    assert section.name == ""
    assert section.version == ""

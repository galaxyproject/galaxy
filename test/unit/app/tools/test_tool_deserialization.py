import pytest

from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.parser.cwl import CwlToolSource
from galaxy.tools import create_tool_from_source

XML_TOOL = """
<tool id="tool_id" name="xml tool" version="1"/>
"""
CWL_TOOL = """
cwlVersion: v1.0
class: CommandLineTool
baseCommand: echo
inputs:
  message:
    type: string
    inputBinding:
      position: 1
outputs: []
"""
YAML_TOOL = """
id: simple_constructs_y
name: simple_constructs_y
version: 1.0
command:
  >
    echo "$booltest"  >> $out_file1;
inputs:
- name: booltest
  type: boolean
  truevalue: booltrue
  falsevalue: boolfalse
  checked: false
outputs:
  out_file1:
    format: txt
"""


class ToolApp(GalaxyDataTestApp):
    name = "galaxy"
    biotools_metadata_source = None
    job_search = None


@pytest.fixture
def tool_app():
    return ToolApp()


def _deserialize(app, tool_source_class, raw_tool_source):
    tool_source = get_tool_source(tool_source_class=tool_source_class, raw_tool_source=raw_tool_source)
    assert type(tool_source).__name__ == tool_source_class
    return create_tool_from_source(app, tool_source=tool_source)


def test_deserialize_xml_tool(tool_app):

    tool = _deserialize(tool_app, tool_source_class="XmlToolSource", raw_tool_source=XML_TOOL)
    assert tool.id == "tool_id"
    assert tool.name == "xml tool"


def test_deserialize_yaml_tool(tool_app):
    tool = _deserialize(tool_app, tool_source_class="YamlToolSource", raw_tool_source=YAML_TOOL)
    assert tool.id == "simple_constructs_y"
    assert tool.name == "simple_constructs_y"


def test_deserialize_cwl_tool(tool_app):
    # Can't verify much about cwl tools at this point
    tool_source = get_tool_source(tool_app, tool_source_class="CwlToolSource", raw_tool_source=CWL_TOOL)
    assert isinstance(tool_source, CwlToolSource)

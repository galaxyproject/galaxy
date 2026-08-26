import json
from types import SimpleNamespace

import pytest

from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.parser.cwl import CwlToolSource
from galaxy.tool_util.provided_metadata import (
    NullToolProvidedMetadata,
    ToolProvidedMetadata,
)
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
- name: data_input
  type: data
  extensions:
    - tabular
    - csv
outputs:
  out_file1:
    format: txt
"""
USER_DEFINED_TOOL = """
class: GalaxyUserTool
id: samtools-reference
version: "0.3"
name: samtools reference
description: Extract or fetch reference sequences from CRAM files
container: quay.io/biocontainers/samtools:1.22.1--h96c455f_0
shell_command: |
  set -euo pipefail; samtools reference '$(inputs.alignment.path)'| bgzip > fasta.gz
inputs:
  - name: alignment
    type: data
    extensions:
      - cram
outputs:
  - name: output1
    type: data
    format: fasta.gz
    from_work_dir: fasta.gz
"""


class ToolApp(GalaxyDataTestApp):
    name = "galaxy"
    biotools_metadata_source = None
    job_search = None
    is_webapp = True


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
    assert tool.inputs["data_input"].extensions == ["tabular", "csv"]


def test_deserialize_user_defined_tool(tool_app):
    tool = _deserialize(tool_app, tool_source_class="YamlToolSource", raw_tool_source=USER_DEFINED_TOOL)
    assert tool.tool_type == "user_defined"
    assert tool.id == "samtools-reference"
    assert tool.name == "samtools reference"
    assert tool.inputs["alignment"].type == "data"
    assert tool.outputs["output1"].format == "fasta.gz"


def test_user_defined_tool_ignores_galaxy_json(tool_app, tmp_path):
    metadata_path = tmp_path / "galaxy.json"
    unnamed_output = {"destination": {"type": "hdas"}, "elements": []}
    metadata_path.write_text(
        json.dumps(
            {
                "output1": {"name": "metadata override", "failed": True},
                "__unnamed_outputs": [unnamed_output],
            }
        )
    )
    job_wrapper = SimpleNamespace(tool_working_directory=str(tmp_path))

    user_tool = _deserialize(tool_app, tool_source_class="YamlToolSource", raw_tool_source=USER_DEFINED_TOOL)
    user_metadata = user_tool.tool_provided_metadata(job_wrapper)
    assert isinstance(user_metadata, NullToolProvidedMetadata)
    assert user_metadata.get_dataset_meta("output1", 1, "unused") == {}
    assert user_metadata.get_unnamed_outputs() == []
    assert not user_metadata.has_failed_outputs()

    regular_tool = _deserialize(tool_app, tool_source_class="YamlToolSource", raw_tool_source=YAML_TOOL)
    regular_metadata = regular_tool.tool_provided_metadata(job_wrapper)
    assert isinstance(regular_metadata, ToolProvidedMetadata)
    assert regular_metadata.get_dataset_meta("output1", 1, "unused") == {
        "name": "metadata override",
        "failed": True,
    }
    assert regular_metadata.get_unnamed_outputs() == [unnamed_output]
    assert regular_metadata.has_failed_outputs()


def test_deserialize_cwl_tool(tool_app):
    # Can't verify much about cwl tools at this point
    tool_source = get_tool_source(tool_app, tool_source_class="CwlToolSource", raw_tool_source=CWL_TOOL)
    assert isinstance(tool_source, CwlToolSource)

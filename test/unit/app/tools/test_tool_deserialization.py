from types import SimpleNamespace

import pytest

from galaxy.model.store.discover import InvalidDiscoveredFilePathError
from galaxy.model.unittest_utils import GalaxyDataTestApp
from galaxy.tool_util.parser import get_tool_source
from galaxy.tool_util.parser.cwl import CwlToolSource
from galaxy.tool_util.provided_metadata import (
    NullToolProvidedMetadata,
    ToolProvidedMetadata,
)
from galaxy.tools import create_tool_from_source

XML_TOOL = """
<tool id="tool_id" name="xml tool" version="1" profile="26.1"/>
"""
XML_TOOL_PROFILE_26_2 = XML_TOOL.replace('profile="26.1"', 'profile="26.2"')
XML_TOOL_WITH_PROVIDED_METADATA = """
<tool id="tool_id" name="xml tool" version="1" profile="26.0">
    <outputs provided_metadata_file="galaxy.json">
        <data name="output" format="txt" />
    </outputs>
</tool>
"""
XML_TOOL_WITH_AUTO_FORMAT = """
<tool id="tool_id" name="xml tool" version="1" profile="26.2">
    <outputs>
        <data name="output" format="auto" />
    </outputs>
</tool>
"""
XML_TOOL_WITH_METADATA_DISCOVERY = """
<tool id="tool_id" name="xml tool" version="1" profile="26.2">
    <outputs>
        <data name="output">
            <discover_datasets discover_via="tool_provided_metadata" />
        </data>
    </outputs>
</tool>
"""
XML_TOOL_WITH_COLLECTION_METADATA_DISCOVERY = """
<tool id="tool_id" name="xml tool" version="1" profile="26.2">
    <outputs>
        <collection name="output" type="list">
            <discover_datasets from_provided_metadata="true" />
        </collection>
    </outputs>
</tool>
"""
INTERACTIVE_TOOL = """
<tool id="interactive_tool" name="interactive tool" tool_type="interactive" version="1">
    <entry_points>
        <entry_point name="Interactive tool"><port>8080</port></entry_point>
    </entry_points>
    <outputs />
</tool>
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
YAML_TOOL_PROFILE_26_2_WITH_AUTO_FORMAT = YAML_TOOL.replace("version: 1.0", 'version: 1.0\nprofile: "26.2"').replace(
    "format: txt", "format: auto"
)
UNRECOGNIZED_YAML_TOOL_WITH_AUTO_FORMAT = YAML_TOOL_PROFILE_26_2_WITH_AUTO_FORMAT.replace(
    "id: simple_constructs_y", "class: FutureUntrustedTool\nid: simple_constructs_y"
)
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
USER_DEFINED_TOOL_WITH_AUTO_FORMAT = USER_DEFINED_TOOL.replace("format: fasta.gz", "format: auto")
USER_DEFINED_TOOL_WITH_METADATA_DISCOVERY = USER_DEFINED_TOOL.replace(
    "    from_work_dir: fasta.gz",
    """    from_work_dir: fasta.gz
    discover_datasets:
      - discover_via: tool_provided_metadata""",
)
USER_DEFINED_TOOL_SPOOFING_UPLOAD = USER_DEFINED_TOOL.replace("id: samtools-reference", "id: upload1")


class ToolApp(GalaxyDataTestApp):
    name = "galaxy"
    biotools_metadata_source = None
    job_search = None
    is_webapp = True


class FutureProfileToolApp(ToolApp):
    # Profile validation is skipped for apps named "tool_shed", which lets tools
    # with profiles newer than VERSION_MAJOR load; fold this back into ToolApp
    # once VERSION_MAJOR >= 26.2.
    name = "tool_shed"


@pytest.fixture
def tool_app():
    return ToolApp()


@pytest.fixture
def future_profile_tool_app():
    return FutureProfileToolApp()


def _deserialize(app, tool_source_class, raw_tool_source):
    tool_source = get_tool_source(tool_source_class=tool_source_class, raw_tool_source=raw_tool_source)
    assert type(tool_source).__name__ == tool_source_class
    return create_tool_from_source(app, tool_source=tool_source)


def test_deserialize_xml_tool(tool_app):
    tool = _deserialize(tool_app, tool_source_class="XmlToolSource", raw_tool_source=XML_TOOL)
    assert tool.id == "tool_id"
    assert tool.name == "xml tool"
    assert tool.tool_source.allows_tool_provided_metadata()


def test_legacy_profile_xml_tool_implicitly_uses_tool_provided_metadata(tool_app, tmp_path):
    tool = _deserialize(
        tool_app,
        tool_source_class="XmlToolSource",
        raw_tool_source=XML_TOOL,
    )
    (tmp_path / "galaxy.json").write_text("{}")

    metadata = tool.tool_provided_metadata(SimpleNamespace(tool_working_directory=str(tmp_path)))

    assert tool.uses_tool_provided_metadata
    assert isinstance(metadata, ToolProvidedMetadata)


def test_legacy_profile_toolshed_tool_implicitly_uses_tool_provided_metadata(tool_app, tmp_path):
    tool_source = get_tool_source(tool_source_class="XmlToolSource", raw_tool_source=XML_TOOL)
    tool = create_tool_from_source(
        tool_app,
        tool_source=tool_source,
        guid="toolshed.example.org/repos/owner/repository/tool_id/1",
    )
    (tmp_path / "galaxy.json").write_text("{}")

    metadata = tool.tool_provided_metadata(SimpleNamespace(tool_working_directory=str(tmp_path)))

    assert tool.uses_tool_provided_metadata
    assert isinstance(metadata, ToolProvidedMetadata)


def test_new_profile_xml_tool_must_opt_in_to_tool_provided_metadata(future_profile_tool_app, tmp_path):
    tool = _deserialize(
        future_profile_tool_app,
        tool_source_class="XmlToolSource",
        raw_tool_source=XML_TOOL_PROFILE_26_2,
    )
    (tmp_path / "galaxy.json").write_text("{}")

    metadata = tool.tool_provided_metadata(SimpleNamespace(tool_working_directory=str(tmp_path)))

    assert not tool.uses_tool_provided_metadata
    assert isinstance(metadata, NullToolProvidedMetadata)


def test_xml_tool_can_opt_in_to_tool_provided_metadata(tool_app, tmp_path):
    tool = _deserialize(
        tool_app,
        tool_source_class="XmlToolSource",
        raw_tool_source=XML_TOOL_WITH_PROVIDED_METADATA,
    )
    (tmp_path / "galaxy.json").write_text("{}")

    metadata = tool.tool_provided_metadata(SimpleNamespace(tool_working_directory=str(tmp_path)))

    assert tool.uses_tool_provided_metadata
    assert isinstance(metadata, ToolProvidedMetadata)


@pytest.mark.parametrize("use_absolute_path", [False, True])
def test_tool_provided_metadata_file_must_be_inside_working_directory(tool_app, tmp_path, use_absolute_path):
    working_directory = tmp_path / "working"
    working_directory.mkdir()
    outside_metadata = tmp_path / "outside.json"
    outside_metadata.write_text("{}")
    metadata_filename = str(outside_metadata) if use_absolute_path else "../outside.json"
    raw_tool_source = XML_TOOL_WITH_PROVIDED_METADATA.replace("galaxy.json", metadata_filename)
    tool = _deserialize(tool_app, tool_source_class="XmlToolSource", raw_tool_source=raw_tool_source)

    with pytest.raises(InvalidDiscoveredFilePathError):
        tool.tool_provided_metadata(SimpleNamespace(tool_working_directory=str(working_directory)))


def test_tool_provided_metadata_file_symlink_must_resolve_inside_working_directory(tool_app, tmp_path):
    working_directory = tmp_path / "working"
    working_directory.mkdir()
    outside_metadata = tmp_path / "outside.json"
    outside_metadata.write_text("{}")
    (working_directory / "galaxy.json").symlink_to(outside_metadata)
    tool = _deserialize(
        tool_app,
        tool_source_class="XmlToolSource",
        raw_tool_source=XML_TOOL_WITH_PROVIDED_METADATA,
    )

    with pytest.raises(InvalidDiscoveredFilePathError):
        tool.tool_provided_metadata(SimpleNamespace(tool_working_directory=str(working_directory)))


def test_tool_provided_metadata_file_symlink_can_resolve_inside_working_directory(tool_app, tmp_path):
    working_directory = tmp_path / "working"
    nested_directory = working_directory / "nested"
    nested_directory.mkdir(parents=True)
    nested_metadata = nested_directory / "metadata.json"
    nested_metadata.write_text("{}")
    (working_directory / "galaxy.json").symlink_to(nested_metadata)
    tool = _deserialize(
        tool_app,
        tool_source_class="XmlToolSource",
        raw_tool_source=XML_TOOL_WITH_PROVIDED_METADATA,
    )

    metadata = tool.tool_provided_metadata(SimpleNamespace(tool_working_directory=str(working_directory)))

    assert isinstance(metadata, ToolProvidedMetadata)


@pytest.mark.parametrize(
    "raw_tool_source",
    [
        XML_TOOL_WITH_AUTO_FORMAT,
        XML_TOOL_WITH_METADATA_DISCOVERY,
        XML_TOOL_WITH_COLLECTION_METADATA_DISCOVERY,
    ],
)
def test_metadata_dependent_output_is_an_explicit_opt_in(future_profile_tool_app, raw_tool_source):
    tool = _deserialize(future_profile_tool_app, tool_source_class="XmlToolSource", raw_tool_source=raw_tool_source)

    assert tool.uses_tool_provided_metadata


def test_new_profile_yaml_tool_can_opt_in_via_metadata_dependent_output(future_profile_tool_app):
    tool = _deserialize(
        future_profile_tool_app,
        tool_source_class="YamlToolSource",
        raw_tool_source=YAML_TOOL_PROFILE_26_2_WITH_AUTO_FORMAT,
    )

    assert tool.uses_tool_provided_metadata


def test_unrecognized_yaml_tool_class_cannot_enable_tool_provided_metadata(future_profile_tool_app):
    tool = _deserialize(
        future_profile_tool_app,
        tool_source_class="YamlToolSource",
        raw_tool_source=UNRECOGNIZED_YAML_TOOL_WITH_AUTO_FORMAT,
    )

    assert not tool.tool_source.allows_tool_provided_metadata()
    assert not tool.uses_tool_provided_metadata


def test_interactive_tool_does_not_implicitly_use_tool_provided_metadata(tool_app, tmp_path):
    tool_app.config.interactivetools_enable = True
    tool = _deserialize(tool_app, tool_source_class="XmlToolSource", raw_tool_source=INTERACTIVE_TOOL)
    (tmp_path / "galaxy.json").write_text("{}")

    metadata = tool.tool_provided_metadata(SimpleNamespace(tool_working_directory=str(tmp_path)))

    assert not tool.uses_tool_provided_metadata
    assert isinstance(metadata, NullToolProvidedMetadata)


def test_interactive_tool_can_explicitly_use_tool_provided_metadata(tool_app):
    tool_app.config.interactivetools_enable = True
    raw_tool_source = INTERACTIVE_TOOL.replace("<outputs />", '<outputs provided_metadata_file="galaxy.json" />')
    tool = _deserialize(tool_app, tool_source_class="XmlToolSource", raw_tool_source=raw_tool_source)

    assert tool.uses_tool_provided_metadata


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


@pytest.mark.parametrize(
    "raw_tool_source",
    [
        USER_DEFINED_TOOL,
        USER_DEFINED_TOOL_WITH_AUTO_FORMAT,
        USER_DEFINED_TOOL_WITH_METADATA_DISCOVERY,
        USER_DEFINED_TOOL_SPOOFING_UPLOAD,
    ],
)
def test_user_defined_tool_cannot_enable_tool_provided_metadata(tool_app, tmp_path, raw_tool_source):
    tool = _deserialize(tool_app, tool_source_class="YamlToolSource", raw_tool_source=raw_tool_source)
    (tmp_path / "galaxy.json").write_text("{}")

    metadata = tool.tool_provided_metadata(SimpleNamespace(tool_working_directory=str(tmp_path)))

    assert not tool.tool_source.allows_tool_provided_metadata()
    assert not tool.uses_tool_provided_metadata
    assert isinstance(metadata, NullToolProvidedMetadata)


def test_deserialize_cwl_tool(tool_app):
    # Can't verify much about cwl tools at this point
    tool_source = get_tool_source(tool_app, tool_source_class="CwlToolSource", raw_tool_source=CWL_TOOL)
    assert isinstance(tool_source, CwlToolSource)
    assert tool_source.allows_tool_provided_metadata()
    assert tool_source.parse_provided_metadata_is_explicit()

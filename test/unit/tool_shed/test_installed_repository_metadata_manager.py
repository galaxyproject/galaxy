from types import SimpleNamespace
from unittest import mock

import pytest

from galaxy.model.tool_shed_install import ToolShedRepository
from galaxy.tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import (
    InstalledRepositoryMetadataManager,
)
from galaxy.util import parse_xml

GUID = "toolshed.example.org/repos/owner/example/tool/1.0"
INSTALLED_REVISION = "0123456789ab"
CURRENT_REVISION = "abcdef012345"
TOOL_CONFIG = f"toolshed.example.org/repos/owner/example/{INSTALLED_REVISION}/example/tool.xml"


@pytest.fixture
def metadata_manager(tmp_path):
    config_path = tmp_path / "shed_tool_conf.xml"
    shed_config = {"config_filename": str(config_path), "tool_path": str(tmp_path / "shed_tools")}
    repository = ToolShedRepository(
        tool_shed="toolshed.example.org",
        name="example",
        owner="owner",
        installed_changeset_revision=INSTALLED_REVISION,
        changeset_revision=CURRENT_REVISION,
        metadata_={"shed_config_filename": str(config_path)},
    )
    app = mock.MagicMock()
    app.toolbox.get_shed_config_dict_by_filename.return_value = shed_config
    app.toolbox.dynamic_confs.return_value = [shed_config]
    app.tool_shed_registry.tool_sheds = {"example": "https://toolshed.example.org"}
    tool = SimpleNamespace(guid=GUID, id="tool", version="1.0")
    app.toolbox.load_tool.return_value = tool
    app.toolbox.materialize_tool.return_value = tool
    manager = InstalledRepositoryMetadataManager(
        app,
        repository=repository,
        shed_config_dict=shed_config,
        relative_install_dir=str(tmp_path),
        repository_files_dir=str(tmp_path),
        metadata_dict={
            "shed_config_filename": str(config_path),
            "tools": [{"guid": GUID, "tool_config": TOOL_CONFIG}],
        },
    )
    return manager, config_path


def reset_metadata(manager):
    # Exercise the reset and real XML writer with newly generated tool metadata.
    with mock.patch.object(manager, "generate_metadata_for_changeset_revision"):
        manager.reset_all_metadata_on_installed_repository()


@pytest.mark.parametrize("in_section", [False, True])
def test_reset_preserves_installed_revision(metadata_manager, in_section):
    manager, config_path = metadata_manager
    tool_xml = f'<tool file="{TOOL_CONFIG}" guid="{GUID}"><version>old</version></tool>'
    if in_section:
        tool_xml = f'<section id="example" name="Example">{tool_xml}</section>'
    config_path.write_text(f'<toolbox tool_path="shed_tools">{tool_xml}</toolbox>')

    reset_metadata(manager)

    tool_elem = parse_xml(config_path).find(".//tool")
    assert tool_elem is not None
    assert tool_elem.findtext("installed_changeset_revision") == INSTALLED_REVISION
    assert tool_elem.get("file") == TOOL_CONFIG
    assert tool_elem.findtext("version") == "1.0"
    assert manager.repository.changeset_revision == CURRENT_REVISION
    manager.app.install_model.context.commit.assert_called_once()


def test_reset_preserves_each_tool_placement_attributes(metadata_manager):
    manager, config_path = metadata_manager
    config_path.write_text(
        '<toolbox tool_path="shed_tools" monitor="true">'
        f'<tool file="{TOOL_CONFIG}" guid="{GUID}" hidden="True" labels="custom"/>'
        '<section id="example" name="Example" version="1">'
        '<label id="label" text="Tools"/>'
        f'<tool file="{TOOL_CONFIG}" guid="{GUID}" hidden="False"/>'
        f'<tool file="{TOOL_CONFIG}" guid="{GUID}"/>'
        '<tool file="unrelated.xml" guid="unrelated" hidden="True"><version>2</version></tool>'
        '</section><label id="end" text="End"/></toolbox>'
    )

    reset_metadata(manager)

    root = parse_xml(config_path).getroot()
    tools = root.findall(".//tool")
    assert [tool.get("hidden") for tool in tools] == ["True", "False", None, "True"]
    assert tools[0].get("labels") == "custom"
    assert [tool.findtext("version") for tool in tools] == ["1.0", "1.0", "1.0", "2"]
    assert dict(tools[-1].attrib.items()) == {"file": "unrelated.xml", "guid": "unrelated", "hidden": "True"}
    assert root.get("monitor") == "true"
    assert [elem.tag for elem in root] == ["tool", "section", "label"]
    section = root.find("section")
    assert section is not None
    assert dict(section.attrib.items()) == {"id": "example", "name": "Example", "version": "1"}
    assert [elem.tag for elem in section] == ["label", "tool", "tool", "tool"]

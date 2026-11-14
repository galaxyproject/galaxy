import os
import subprocess
import sys
import textwrap
from typing import Optional
from unittest import mock

from galaxy.app_unittest_utils.toolbox_support import (
    BaseToolBoxTestCase,
    SimplifiedToolBox,
)
from galaxy.tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import (
    InstalledRepositoryMetadataManager,
)
from galaxy.tool_shed.galaxy_install.tools import tool_panel_manager
from galaxy.util import (
    Element,
    parse_xml,
    SubElement,
)
from galaxy.util.tool_shed import common_util
from tool_shed.tools import tool_version_manager
from ._util import TestToolShedApp

DEFAULT_GUID = "123456"

UNINSTALLED_GUID = "github.com/galaxyproject/example/test_tool/0.2"

UNINSTALL_IN_OTHER_PROCESS = textwrap.dedent("""
    import sys

    from galaxy.tool_shed.galaxy_install.tools.tool_panel_manager import ToolPanelManager

    conf_path, tool_path, guid = sys.argv[1:]
    print("ready", flush=True)
    sys.stdin.readline()
    ToolPanelManager(app=None).remove_from_shed_tool_config(
        {"config_filename": conf_path, "tool_path": tool_path},
        {"tools": [{"guid": guid, "tool_config": "tool.xml"}]},
    )
    """)


class TestToolPanelManager(BaseToolBoxTestCase):
    def setUp(self):
        super().setUp()
        self.ts_app = TestToolShedApp()

    def get_new_toolbox(self):
        return SimplifiedToolBox(self)

    def test_handle_tool_panel_section(self):
        self._init_tool()
        self._add_config("""<toolbox><section id="tid" name="test"><tool file="tool.xml" /></section></toolbox>""")
        toolbox = self.toolbox
        tpm = self.tpm
        # Test fetch existing section by id.
        section_id, section = tpm.handle_tool_panel_section(toolbox, tool_panel_section_id="tid")
        assert section_id == "tid"
        assert len(section.elems) == 1  # tool.xml
        assert section.id == "tid"
        assert len(toolbox._tool_panel) == 2  # section + built-in converters section

        section_id, section = tpm.handle_tool_panel_section(toolbox, new_tool_panel_section_label="tid2")
        assert section_id == "tid2"
        assert len(section.elems) == 0  # new section
        assert section.id == "tid2"
        assert len(toolbox._tool_panel) == 3  # 2 sections + built-in converters section

        # Test re-fetch new section by same id.
        section_id, section = tpm.handle_tool_panel_section(toolbox, new_tool_panel_section_label="tid2")
        assert section_id == "tid2"
        assert len(section.elems) == 0  # new section
        assert section.id == "tid2"
        assert len(toolbox._tool_panel) == 3  # 2 sections + built-in converters section

    def test_add_tool_to_panel(self):
        self._init_ts_tool(guid=DEFAULT_GUID)
        self._init_dynamic_tool_conf()
        tool_path = self._tool_path()
        new_tools = [{"guid": DEFAULT_GUID, "tool_config": tool_path}]
        repository_tools_tups = [
            (
                tool_path,
                DEFAULT_GUID,
                self.tool,
            )
        ]
        _, section = self.toolbox.get_section("tid1", create_if_needed=True)
        tpm = self.tpm
        tool_panel_dict = tpm.generate_tool_panel_dict_for_new_install(
            tool_dicts=new_tools,
            tool_section=section,
        )
        tpm.add_to_tool_panel(
            repository_name="test_repo",
            repository_clone_url="http://github.com/galaxyproject/example.git",
            changeset_revision="0123456789abcde",
            repository_tools_tups=repository_tools_tups,
            owner="devteam",
            shed_tool_conf="tool_conf.xml",
            tool_panel_dict=tool_panel_dict,
        )
        self._verify_tool_confs()

    def test_add_twice(self):
        self._init_dynamic_tool_conf()
        previous_guid: Optional[str] = None
        for v in "1", "2", "3":
            self.__toolbox = self.get_new_toolbox()
            changeset = f"0123456789abcde{v}"
            guid = DEFAULT_GUID + (f"v/{v}")
            tool = self._init_ts_tool(guid=guid, filename=f"tool_v{v}.xml", version=v)
            tool_path = self._tool_path(name=f"tool_v{v}.xml")
            new_tools = [{"guid": guid, "tool_config": tool_path}]
            self._repo_install(changeset)
            repository_tools_tups = [
                (
                    tool_path,
                    guid,
                    tool,
                )
            ]
            _, section = self.toolbox.get_section("tid1", create_if_needed=True)
            tpm = self.tpm
            tool_panel_dict = tpm.generate_tool_panel_dict_for_new_install(
                tool_dicts=new_tools,
                tool_section=section,
            )
            tpm.add_to_tool_panel(
                repository_name="example",
                repository_clone_url="github.com",
                changeset_revision=changeset,
                repository_tools_tups=repository_tools_tups,
                owner="galaxyproject",
                shed_tool_conf="tool_conf.xml",
                tool_panel_dict=tool_panel_dict,
            )
            self._verify_tool_confs()
            section = self.toolbox._tool_panel["tid1"]
            # New GUID replaced old one in tool panel but both
            # appear in integrated tool panel.
            if previous_guid:
                assert (f"tool_{previous_guid}") not in section.panel_items()
            assert (f"tool_{guid}") in self.toolbox._integrated_tool_panel["tid1"].panel_items()
            previous_guid = guid

    def test_uninstall_in_section(self):
        self._setup_two_versions_remove_one(section=True, uninstall=True)
        self._verify_version_2_removed_from_panel()
        # Not in tool conf because it was uninstalled.
        assert (
            "github.com/galaxyproject/example/test_tool/0.2"
            not in open(os.path.join(self.test_directory, "tool_conf.xml")).read()
        )
        new_toolbox = self.get_new_toolbox()
        assert (
            "tool_github.com/galaxyproject/example/test_tool/0.2" not in new_toolbox._integrated_tool_panel["tid"].elems
        )
        self._verify_tool_confs()

    def test_uninstall_outside_section(self):
        self._setup_two_versions_remove_one(section=False, uninstall=True)
        self._verify_version_2_removed_from_panel(section=False)
        # Still in tool conf since not uninstalled only deactivated...
        assert (
            "github.com/galaxyproject/example/test_tool/0.2"
            not in open(os.path.join(self.test_directory, "tool_conf.xml")).read()
        )
        self._verify_tool_confs()

        self._remove_repository_contents("github.com/galaxyproject/example/test_tool/0.1", uninstall=True)

        # Now no versions of this tool are returned by new toolbox.
        new_toolbox = self.get_new_toolbox()
        all_versions = new_toolbox.get_tool("test_tool", get_all_versions=True)
        assert not all_versions

    def test_uninstall_in_other_process_survives_concurrent_install(self):
        new_elem = Element("tool", attrib={"file": "new_tool.xml", "guid": DEFAULT_GUID})
        SubElement(new_elem, "id").text = DEFAULT_GUID
        conf = self._race_uninstall_in_other_process(
            lambda: self.tpm.add_to_shed_tool_config(self._shed_tool_conf_dict(), [new_elem])
        )
        assert UNINSTALLED_GUID not in conf
        assert DEFAULT_GUID in conf

    def test_uninstall_in_other_process_survives_concurrent_metadata_reset(self):
        clone_url = "https://github.com/repos/galaxyproject/example"
        with mock.patch.object(common_util, "generate_clone_url_for_installed_repository", return_value=clone_url):
            metadata_manager = InstalledRepositoryMetadataManager(
                self.app,
                tpm=self.tpm,
                repository=self._repo_install(changeset="1"),
                repository_clone_url=clone_url,
                shed_config_dict=self._shed_tool_conf_dict(),
                relative_install_dir=self.test_directory,
                repository_files_dir=self.test_directory,
            )
            with mock.patch.object(metadata_manager, "get_repository_tools_tups", return_value=[]):
                conf = self._race_uninstall_in_other_process(metadata_manager.update_in_shed_tool_config)
        assert UNINSTALLED_GUID not in conf
        assert "github.com/galaxyproject/example/test_tool/0.1" in conf

    def _race_uninstall_in_other_process(self, write_shed_tool_conf):
        """Uninstall from a second process between this process's read and write of the shed tool conf.

        Returns the shed tool conf contents once both writers are done.
        """
        self._init_tool()
        self._setup_two_versions_in_config(section=False)
        assert self.toolbox
        conf_path = self._tool_conf_path()
        write_unpatched = tool_panel_manager.ToolPanelManager.config_elems_to_xml_file
        uninstaller = subprocess.Popen(
            [sys.executable, "-c", UNINSTALL_IN_OTHER_PROCESS, conf_path, self.test_directory, UNINSTALLED_GUID],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
        )
        try:
            assert uninstaller.stdout
            assert uninstaller.stdout.readline().strip() == "ready"

            def uninstall_then_write(tpm, *args, **kwargs):
                assert uninstaller.stdin
                uninstaller.stdin.write("go\n")
                uninstaller.stdin.close()
                try:
                    uninstaller.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Blocked on the shed tool conf lock this process holds.
                    pass
                return write_unpatched(tpm, *args, **kwargs)

            with mock.patch.object(
                tool_panel_manager.ToolPanelManager, "config_elems_to_xml_file", uninstall_then_write
            ):
                write_shed_tool_conf()
            assert uninstaller.wait(timeout=60) == 0
        finally:
            if uninstaller.poll() is None:
                uninstaller.kill()
        with open(conf_path) as fh:
            return fh.read()

    def _shed_tool_conf_dict(self):
        return {"config_filename": self._tool_conf_path(), "tool_path": self.test_directory}

    def _setup_two_versions_remove_one(self, section, uninstall):
        self._init_tool()
        self._setup_two_versions_in_config(section=section)
        self._setup_two_versions()
        self._remove_repository_contents("github.com/galaxyproject/example/test_tool/0.2", uninstall=uninstall)

    def _verify_version_2_removed_from_panel(self, section=True):
        # Check that test_tool now only has one version...
        # We load a new toolbox
        new_toolbox = self.get_new_toolbox()
        all_versions = new_toolbox.get_tool("test_tool", get_all_versions=True)
        assert len(all_versions) == 1

        # Check that tool panel has reverted to old value...
        if section:
            section = new_toolbox._tool_panel["tid"]
            assert len(section.elems) == 1
            assert next(iter(section.elems.values())).id == "github.com/galaxyproject/example/test_tool/0.1"

            assert (
                "github.com/galaxyproject/example/test_tool/0.2" not in new_toolbox._integrated_tool_panel["tid"].elems
            )
        else:
            assert next(iter(new_toolbox._tool_panel.values())).id == "github.com/galaxyproject/example/test_tool/0.1"
            assert "github.com/galaxyproject/example/test_tool/0.2" not in new_toolbox._integrated_tool_panel

    def _remove_repository_contents(self, guid, uninstall, shed_tool_conf="tool_conf.xml"):
        tool = self.toolbox.get_tool(guid)
        repository = tool.tool_shed_repository
        self.tpm.remove_repository_contents(
            repository=repository,
            shed_tool_conf=shed_tool_conf,
            uninstall=uninstall,
        )

    def _verify_tool_confs(self):
        self._assert_valid_xml(self.integrated_tool_panel_path)
        self._assert_valid_xml(os.path.join(self.test_directory, "tool_conf.xml"))

    def _assert_valid_xml(self, filename):
        try:
            parse_xml(filename)
        except Exception:
            with open(filename) as fh:
                content = fh.read()
            message = f"file {filename} does not contain valid XML, content {content}"
            raise AssertionError(message)

    def _init_ts_tool(self, guid=DEFAULT_GUID, **kwds):
        tool = self._init_tool(**kwds)
        tool.guid = guid
        tool.version = kwds.get("version", "1.0")
        return tool

    @property
    def tpm(self):
        return tool_panel_manager.ToolPanelManager(self.app)

    @property
    def tvm(self):
        return tool_version_manager.ToolVersionManager(self.ts_app)

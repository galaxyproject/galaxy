import collections
import json
import logging
import os
import string
from typing import Optional

from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.config_watchers import ConfigWatchers
from galaxy.model import tool_shed_install
from galaxy.model.tool_shed_install import mapping
from galaxy.tools import ToolBox
from galaxy.tools.cache import ToolCache
from galaxy.util.unittest import TestCase

log = logging.getLogger(__name__)


CONFIG_TEST_TOOL_VERSION_TEMPLATE = string.Template(
    """    <tool file="tool.xml" guid="github.com/galaxyproject/example/test_tool/0.${version}">
            <tool_shed>github.com</tool_shed>
            <repository_name>example</repository_name>
            <repository_owner>galaxyproject</repository_owner>
            <installed_changeset_revision>${version}</installed_changeset_revision>
            <id>github.com/galaxyproject/example/test_tool/0.${version}</id>
            <version>0.${version}</version>
        </tool>
    """
)
CONFIG_TEST_TOOL_VERSION_1 = CONFIG_TEST_TOOL_VERSION_TEMPLATE.safe_substitute(dict(version="1"))
CONFIG_TEST_TOOL_VERSION_2 = CONFIG_TEST_TOOL_VERSION_TEMPLATE.safe_substitute(dict(version="2"))

REPO_TYPE = collections.namedtuple(
    "REPO_TYPE",
    "tool_shed owner name changeset_revision installed_changeset_revision description status",
)
DEFAULT_TEST_REPO = REPO_TYPE("github.com", "galaxyproject", "example", "1", "1", "description", "OK")


class SimplifiedToolBox(ToolBox):
    def __init__(self, test_case: "BaseToolBoxTestCase"):
        app = test_case.app
        app.watchers.tool_config_watcher.reload_callback = lambda: reload_callback(test_case)
        # Handle app/config stuff needed by toolbox but not by tools.
        app.tool_cache = ToolCache() if not hasattr(app, "tool_cache") else app.tool_cache
        config_files = test_case.config_files
        tool_root_dir = test_case.test_directory
        super().__init__(
            config_files,
            tool_root_dir,
            app,
        )
        # Need to start thread now for new reload callback to take effect
        self.app.watchers.start()


class BaseToolBoxTestCase(TestCase, UsesTools):
    _toolbox: Optional[SimplifiedToolBox] = None

    @property
    def integrated_tool_panel_path(self):
        return os.path.join(self.test_directory, "integrated_tool_panel.xml")

    def assert_integerated_tool_panel(self, exists=True):
        does_exist = os.path.exists(self.integrated_tool_panel_path)
        if exists:
            assert does_exist
        else:
            assert not does_exist

    @property
    def toolbox(self):
        if self._toolbox is None:
            self.app._toolbox = self._toolbox = SimplifiedToolBox(self)
        return self._toolbox

    def setUp(self):
        self.reindexed = False
        self.setup_app()
        install_model = mapping.init("sqlite:///:memory:", create_tables=True)
        self.app.tool_cache = ToolCache()
        self.app.install_model = install_model
        self.app.reindex_tool_search = self.__reindex  # type: ignore[method-assign]
        itp_config = os.path.join(self.test_directory, "integrated_tool_panel.xml")
        self.app.config.integrated_tool_panel_config = itp_config
        self.app.watchers = ConfigWatchers(self.app)
        self._toolbox = None
        self.config_files = []

    def tearDown(self):
        self.app.watchers.shutdown()

    def _repo_install(self, changeset, config_filename=None):
        metadata = {
            "tools": [
                {
                    "add_to_tool_panel": False,  # to have repository.includes_tools_for_display_in_tool_panel=False in InstalledRepositoryManager.activate_repository()
                    "guid": f"github.com/galaxyproject/example/test_tool/0.{changeset}",
                    "tool_config": "tool.xml",
                }
            ],
        }
        if config_filename:
            metadata["shed_config_filename"] = config_filename
        repository = tool_shed_install.ToolShedRepository(metadata_=metadata)
        repository.tool_shed = DEFAULT_TEST_REPO.tool_shed
        repository.owner = DEFAULT_TEST_REPO.owner
        repository.name = DEFAULT_TEST_REPO.name
        repository.changeset_revision = changeset
        repository.installed_changeset_revision = changeset
        repository.deleted = False
        repository.uninstalled = False
        self.app.install_model.context.add(repository)
        session = self.app.install_model.context
        session.commit()
        return repository

    def _setup_two_versions(self):
        self._repo_install(changeset="1")
        version1 = tool_shed_install.ToolVersion()
        version1.tool_id = "github.com/galaxyproject/example/test_tool/0.1"
        self.app.install_model.context.add(version1)
        session = self.app.install_model.context
        session.commit()

        self._repo_install(changeset="2")
        version2 = tool_shed_install.ToolVersion()
        version2.tool_id = "github.com/galaxyproject/example/test_tool/0.2"
        self.app.install_model.context.add(version2)
        session = self.app.install_model.context
        session.commit()

        version_association = tool_shed_install.ToolVersionAssociation()
        version_association.parent_id = version1.id
        version_association.tool_id = version2.id

        self.app.install_model.context.add(version_association)
        session = self.app.install_model.context
        session.commit()

    def _setup_two_versions_in_config(self, section=False):
        if section:
            template = """<toolbox tool_path="%s">
    <section id="tid" name="TID" version="">
        %s
    </section>
    <section id="tid" name="TID" version="">
        %s
    </section>
</toolbox>"""
        else:
            template = """<toolbox tool_path="%s">
    %s
    %s
</toolbox>"""
        self._add_config(template % (self.test_directory, CONFIG_TEST_TOOL_VERSION_1, CONFIG_TEST_TOOL_VERSION_2))

    def _add_config(self, content, name="tool_conf.xml"):
        is_json = name.endswith(".json")
        path = self._tool_conf_path(name=name)
        with open(path, "w") as f:
            if not is_json or isinstance(content, str):
                f.write(content)
            else:
                json.dump(content, f)
        self.config_files.append(path)

    def _init_dynamic_tool_conf(self):
        # Add a dynamic tool conf (such as a ToolShed managed one) to list of configs.
        self._add_config(f"""<toolbox tool_path="{self.test_directory}"></toolbox>""")

    def _tool_conf_path(self, name="tool_conf.xml"):
        path = os.path.join(self.test_directory, name)
        return path

    def _tool_path(self, name="tool.xml"):
        path = os.path.join(self.test_directory, name)
        return path

    def __reindex(self):
        self.reindexed = True


def reload_callback(test_case):
    test_case.app.tool_cache.cleanup()
    log.debug("Reload callback called, toolbox contains %s", test_case._toolbox._tool_versions_by_id)
    test_case._toolbox = test_case.app.toolbox = SimplifiedToolBox(test_case)
    log.debug("After callback toolbox contains %s", test_case._toolbox._tool_versions_by_id)

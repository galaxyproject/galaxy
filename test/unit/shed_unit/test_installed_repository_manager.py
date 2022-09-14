import os
from typing import (
    Any,
    Dict,
)
from unittest.mock import MagicMock

from galaxy.tool_shed.galaxy_install.install_manager import InstallRepositoryManager
from galaxy.tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
from galaxy.tool_shed.galaxy_install.update_repository_manager import UpdateRepositoryManager
from galaxy.tool_shed.util import (
    hg_util,
    repository_util,
)
from galaxy.util.tool_shed import common_util
from ..app.tools.test_toolbox import (
    BaseToolBoxTestCase,
    DEFAULT_TEST_REPO,
)


class ToolShedRepoBaseTestCase(BaseToolBoxTestCase):
    def setUp(self):
        super().setUp()
        self._init_dynamic_tool_conf()
        self.app.config.tool_configs = self.config_files
        self.app.config.manage_dependency_relationships = False
        self.app.toolbox = self.toolbox

    def _setup_repository(self):
        return self._repo_install(changeset="1", config_filename=self.config_files[0])


class InstallRepositoryManagerTestCase(ToolShedRepoBaseTestCase):
    def setUp(self):
        super().setUp()
        self.irm = InstallRepositoryManager(self.app)
        self.app.config.enable_tool_shed_check = False
        self.app.update_repository_manager = UpdateRepositoryManager(self.app)

    def test_tool_shed_repository_install(self):
        hg_util.clone_repository = MagicMock(return_value=(True, None))
        self._install_tool_shed_repository(start_status="New", end_status="Installed", changeset_revision="1")
        hg_util.clone_repository.assert_called_with(
            "github.com/repos/galaxyproject/example",
            os.path.abspath(os.path.join("../shed_tools", "github.com/repos/galaxyproject/example/1/example")),
            "1",
        )

    def test_tool_shed_repository_update(self):
        common_util.get_tool_shed_url_from_tool_shed_registry = MagicMock(return_value="https://github.com")
        repository_util.get_tool_shed_status_for_installed_repository = MagicMock(
            return_value={"revision_update": "false"}
        )
        hg_util.pull_repository = MagicMock()
        hg_util.update_repository = MagicMock(return_value=(True, None))
        self._install_tool_shed_repository(start_status="Installed", end_status="Installed", changeset_revision="2")
        assert hg_util.pull_repository.call_args[0][0].endswith("github.com/repos/galaxyproject/example/1/example")
        assert hg_util.pull_repository.call_args[0][1] == "https://github.com/repos/galaxyproject/example"
        assert hg_util.pull_repository.call_args[0][2] == "2"
        assert hg_util.update_repository.call_args[0][0].endswith("github.com/repos/galaxyproject/example/1/example")
        assert hg_util.update_repository.call_args[0][1] == "2"

    def _install_tool_shed_repository(self, start_status, end_status, changeset_revision):
        repository = self._setup_repository()
        repository.status = start_status
        repo_info_dict: Dict[str, Any] = {
            "example": (
                "description",
                "github.com/repos/galaxyproject/example",
                changeset_revision,
                changeset_revision,
                "galaxyproject",
                [],
                [],
            )
        }
        self.irm.install_tool_shed_repository(
            repository,
            repo_info_dict,
            "section_key",
            self.app.config.tool_configs[0],
            "../shed_tools",
            False,
            False,
            reinstalling=False,
        )
        assert repository.status == end_status
        assert repository.changeset_revision == changeset_revision


class InstalledRepositoryManagerTestCase(ToolShedRepoBaseTestCase):
    def setUp(self):
        super().setUp()
        self.irm = InstalledRepositoryManager(self.app)

    def test_uninstall_repository(self):
        repository = self._setup_repository()
        assert repository.uninstalled is False
        self.irm.uninstall_repository(repository=repository, remove_from_disk=True)
        assert repository.uninstalled is True

    def test_deactivate_repository(self):
        self._deactivate_repository()

    def test_activate_repository(self):
        repository = self._deactivate_repository()
        self.irm.activate_repository(repository)
        assert repository.status == self.app.install_model.ToolShedRepository.installation_status.INSTALLED

    def test_create_or_update_tool_shed_repository_update(self):
        repository = self._setup_repository()
        self._create_or_update_tool_shed_repository(repository=repository, changeset_revision="2")

    def test_create_or_update_tool_shed_repository_create(self):
        self._create_or_update_tool_shed_repository(repository=None, changeset_revision="2")

    def _create_or_update_tool_shed_repository(self, repository=None, changeset_revision="2"):
        if repository is None:
            repository = DEFAULT_TEST_REPO
        new_repository = repository_util.create_or_update_tool_shed_repository(
            app=self.app,
            name=repository.name,
            description=repository.description,
            installed_changeset_revision=repository.installed_changeset_revision,
            ctx_rev=repository.changeset_revision,
            repository_clone_url="https://github.com/galaxyproject/example/test_tool/0.%s"
            % repository.installed_changeset_revision,  # not needed if owner is given
            status=repository.status,
            metadata_dict=None,
            current_changeset_revision=str(int(repository.changeset_revision) + 1),
            owner=repository.owner,
            dist_to_shed=False,
        )
        assert new_repository.changeset_revision == changeset_revision

    def _deactivate_repository(self):
        repository = self._setup_repository()
        assert repository.uninstalled is False
        self.irm.uninstall_repository(repository=repository, remove_from_disk=False)
        assert repository.uninstalled is False
        assert repository.status == self.app.install_model.ToolShedRepository.installation_status.DEACTIVATED
        return repository

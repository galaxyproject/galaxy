from tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
from ..tools.test_toolbox import BaseToolBoxTestCase


class InstalledRepositoryManagerTestCase(BaseToolBoxTestCase):

    def test_uninstall_repository(self):
        repository = self._setup_repository()
        assert repository.uninstalled is False
        irm = InstalledRepositoryManager(self.app)
        irm.uninstall_repository(repository=repository, remove_from_disk=True)
        assert repository.uninstalled is True

    def test_deactivate_repository(self):
        self._deactivate_repository()

    def test_activate_repository(self):
        irm, repository = self._deactivate_repository()
        irm.activate_repository(repository)
        assert repository.status == self.app.install_model.ToolShedRepository.installation_status.INSTALLED

    def _deactivate_repository(self):
        repository = self._setup_repository()
        assert repository.uninstalled is False
        irm = InstalledRepositoryManager(self.app)
        irm.uninstall_repository(repository=repository, remove_from_disk=False)
        assert repository.uninstalled is False
        assert repository.status == self.app.install_model.ToolShedRepository.installation_status.DEACTIVATED
        return irm, repository

    def _setup_repository(self):
        self._init_dynamic_tool_conf()
        self.app.config.tool_configs = self.config_files
        self.app.config.manage_dependency_relationships = False
        self.app.toolbox = self.toolbox
        return self._repo_install(changeset='1', config_filename=self.config_files[0])

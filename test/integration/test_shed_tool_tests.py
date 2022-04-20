import os

from galaxy_test.base.populators import skip_if_toolshed_down
from galaxy_test.base.uses_shed import UsesShed
from galaxy_test.driver import integration_util


class ToolShedToolTestIntegrationTestCase(integration_util.IntegrationTestCase, UsesShed):

    """Test data manager installation and table reload through the API"""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.configure_shed_and_conda(config)

    @skip_if_toolshed_down
    def test_tool_test(self):
        self.install_repository("devteam", "fastqc", "3d0c7bdf12f5")
        self._run_tool_test("toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.73+galaxy0")


class ToolShedDatatypeTestIntegrationTestCase(integration_util.IntegrationTestCase, UsesShed):

    """Test datatype installation"""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.configure_shed(config)

    def handle_reconfigure_galaxy_config_kwds(self, config):
        config["tool_shed_config_file"] = os.path.join(self.shed_tools_dir, "shed_tool_conf.xml")

    @skip_if_toolshed_down
    def test_datatype_installation(self):
        datatypes = self._get("datatypes").json()
        assert "cond" not in datatypes
        self.install_repository("sblanck", "smagexp_datatypes", "f174dc3d2641")
        datatypes = self._get("datatypes").json()
        assert "cond" in datatypes
        # Make sure datatype survives restart
        self.restart(handle_reconfig=self.handle_reconfigure_galaxy_config_kwds)
        datatypes = self._get("datatypes").json()
        assert "cond" in datatypes

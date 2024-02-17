from galaxy_test.base.populators import skip_if_toolshed_down
from galaxy_test.driver import integration_util
from galaxy_test.driver.uses_shed import UsesShed


class TestToolShedToolTestIntegration(integration_util.IntegrationTestCase, UsesShed):
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

from base import integration_util

from .uses_shed import UsesShed


class ToolShedToolTestIntegrationTestCase(integration_util.IntegrationTestCase, UsesShed):

    """Test data manager installation and table reload through the API"""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls.configure_shed_and_conda(config)

    def test_tool_test(self):
        self.install_repository("devteam", "fastqc", "ff9530579d1f")
        self._run_tool_test("toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.71")

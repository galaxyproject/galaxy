from galaxy_test.driver.uses_shed import UsesShed
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

FASTQC_GUID = "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.73+galaxy0"


class TestToolShedToolIds(SeleniumIntegrationTestCase, UsesShed):
    run_as_admin = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.configure_shed(config)

    def setUp(self):
        super().setUp()
        self.install_repository("devteam", "fastqc", "3d0c7bdf12f5")  # 0.73+galaxy0

    @selenium_test
    def test_tool_open_by_tool_shed_guid(self):
        self.home()
        self.tool_open(FASTQC_GUID)
        self._assert_fastqc_form_open()
        self.screenshot("tool_panel_search_by_tool_shed_id")

    @selenium_test
    def test_tools_list_card_by_tool_shed_guid(self):
        self.home()
        self.components.tool_panel.discover_tools_link.wait_for_and_click()
        tools_list = self.components.tools_list
        tools_list._.wait_for_visible()
        tools_list.search_input.wait_for_and_send_keys("FastQC")
        tools_list.tool_card(tool_id=FASTQC_GUID).wait_for_visible()
        tools_list.version_button(tool_id=FASTQC_GUID).wait_for_visible()
        tools_list.favorite_tool_button(tool_id=FASTQC_GUID).wait_for_visible()
        tools_list.toggle_help(tool_id=FASTQC_GUID).wait_for_and_click()
        tools_list.tool_help(tool_id=FASTQC_GUID).wait_for_visible()
        self.screenshot("tools_list_tool_shed_tool_help")
        tools_list.open_tool_button(tool_id=FASTQC_GUID).wait_for_and_click()
        tools_list._.wait_for_absent()
        self._assert_fastqc_form_open()

    def _assert_fastqc_form_open(self):
        tool_version = self.components.tool_form.tool_version.wait_for_visible()
        assert tool_version.get_attribute("data-version") == "0.73+galaxy0"

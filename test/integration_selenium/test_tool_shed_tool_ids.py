from galaxy_test.driver.uses_shed import UsesShed
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

COMPOSE_TEXT_PARAM_GUID = "toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param/compose_text_param/0.1.1"


class TestToolShedToolIds(SeleniumIntegrationTestCase, UsesShed):
    run_as_admin = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.configure_shed(config)

    def setUp(self):
        super().setUp()
        self.install_repository("iuc", "compose_text_param", "e188c9826e0f")  # 0.1.1

    @selenium_test
    def test_tool_open_by_tool_shed_guid(self):
        self.home()
        # A special-form tool: the click loads into the hidden galaxy_main frame, so check the panel, not a form.
        self.tool_open(COMPOSE_TEXT_PARAM_GUID)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("tool_panel_search_by_tool_shed_id")

    @selenium_test
    def test_tools_list_card_by_tool_shed_guid(self):
        self.home()
        self.components.tool_panel.discover_tools_link.wait_for_and_click()
        tools_list = self.components.tools_list
        tools_list._.wait_for_visible()
        tools_list.search_input.wait_for_and_send_keys("compose text")
        tools_list.tool_card(tool_id=COMPOSE_TEXT_PARAM_GUID).wait_for_visible()
        tools_list.version_button(tool_id=COMPOSE_TEXT_PARAM_GUID).wait_for_visible()
        tools_list.favorite_tool_button(tool_id=COMPOSE_TEXT_PARAM_GUID).wait_for_visible()
        tools_list.toggle_help(tool_id=COMPOSE_TEXT_PARAM_GUID).wait_for_and_click()
        tools_list.tool_help(tool_id=COMPOSE_TEXT_PARAM_GUID).wait_for_visible()
        self.screenshot("tools_list_tool_shed_tool_help")

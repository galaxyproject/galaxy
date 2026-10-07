from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

TEST_FILTER_MODULES = "galaxy.selenium.toolbox"
TEST_SECTION_FILTERS = "filters:restrict_test"


class TestToolboxFiltersSeleniumIntegration(SeleniumIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["user_tool_section_filters"] = TEST_SECTION_FILTERS
        config["toolbox_filter_base_modules"] = TEST_FILTER_MODULES

    @selenium_test
    def test_toolbox_filters(self):
        """
        Test applying and removing a toolbox filter.

        This test applies the filter galaxy.selenium.filters.toolbox:restrict_test and confirms that
        the specified section is no longer displayed in the browser.
        """
        self.register()
        self.components.tool_panel.tool_box.wait_for_visible()
        # The tool panel section should be visible and clickable at this stage
        section = self.find_element_by_link_text("Test Section")
        self.move_to_and_click(section)
        self.navigate_to_user_preferences()
        self.components.preferences.toolbox_filters.wait_for_and_click()
        self.screenshot("toolbox_filters_landing")
        sibling_text = "This tool filter will disable the Test Section section."
        component = self.components.toolbox_filters.input(description=sibling_text)
        filter_upload = component.wait_for_visible()
        self.move_to_and_click(filter_upload)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("toolbox_filters_swapped")
        self.components.toolbox_filters.submit.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.home()
        self.components.tool_panel.tool_box.wait_for_visible()
        # But now the section should be gone from the panel entirely
        assert "Test Section" not in self._tool_section_titles()

    def _tool_section_titles(self):
        links = self.find_elements_by_selector(".tool-panel-section .title-link")
        return [link.text for link in links]

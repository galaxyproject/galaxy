from selenium.common.exceptions import NoSuchElementException

from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase
)

TEST_FILTER_MODULES = 'galaxy.selenium.toolbox'
TEST_SECTION_FILTERS = 'filters:restrict_test'


class ToolboxFiltersSeleniumIntegrationTestCase(SeleniumIntegrationTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["user_tool_section_filters"] = TEST_SECTION_FILTERS
        config["toolbox_filter_base_modules"] = TEST_FILTER_MODULES

    @selenium_test
    def test_toolbox_filters(self):
        '''
        Test applying and removing a toolbox filter.

        This test applies the filter galaxy.selenium.filters.toolbox:restrict_test and confirms that
        the specified section is no longer displayed in the browser.
        '''
        self.register()
        # The tool panel section should be visible and clickable at this stage
        section = self.driver.find_element_by_link_text('Test Section')
        self.action_chains().move_to_element(section).click().perform()
        self.navigate_to_user_preferences()
        self.components.preferences.toolbox_filters.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        sibling_text = 'This tool filter will disable the Test Section section.'
        # This is the least terrible way I've found to get the right element.
        filter_upload = self.driver.find_element_by_xpath("//span[contains(. ,'%s')]/../div//label" % sibling_text)
        self.action_chains().move_to_element(filter_upload).click().perform()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.components.toolbox_filters.submit.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.home()
        # But now it should raise NoSuchElementException
        self.assertRaises(NoSuchElementException, lambda: self.driver.find_element_by_link_text('Test Section'))

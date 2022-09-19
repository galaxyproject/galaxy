from galaxy_test.base.populators import skip_if_site_down
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class DataSourceTestCase(SeleniumTestCase, UsesHistoryItemAssertions):

    ensure_registered = True

    @selenium_test
    @managed_history
    @skip_if_site_down("https://genome.ucsc.edu/cgi-bin/hgTables")
    def test_ucsc_table_direct1_data_source(self):
        self.home()
        self.datasource_tool_open("ucsc_table_direct1")
        self.screenshot("ucsc_table_browser_first_page")
        checkbox = self.wait_for_selector("#checkboxGalaxy")
        assert checkbox.get_attribute("checked") == "true"
        submit_button = self.wait_for_selector("#hgta_doTopSubmit")
        submit_button.click()
        self.screenshot("ucsc_table_browser_second_page")
        self.wait_for_selector("#hgta_doGalaxyQuery").click()
        self.history_panel_wait_for_hid_ok(1)
        # Make sure we're still logged in (xref https://github.com/galaxyproject/galaxy/issues/11374)
        self.components.masthead.logged_in_only.wait_for_visible()

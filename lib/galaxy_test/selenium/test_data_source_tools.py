import pytest
from selenium.webdriver.support.ui import Select

from galaxy.util.unittest_utils import skip_if_site_down
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class TestDataSource(SeleniumTestCase, UsesHistoryItemAssertions):
    ensure_registered = True

    @pytest.mark.skip("Skipping UCSC table direct1 data source test, chromedriver fails captcha")
    @selenium_test
    @managed_history
    @skip_if_site_down("https://genome.ucsc.edu/cgi-bin/hgTables")
    def test_ucsc_table_direct1_data_source(self):
        self.home()
        self.datasource_tool_open("ucsc_table_direct1")
        self.screenshot("ucsc_table_browser_first_page")
        # only 4mb instead of 10 times that for human by default
        Select(self.wait_for_selector("#org")).select_by_value("Tree shrew")
        checkbox = self.wait_for_selector("#checkboxGalaxy")
        assert checkbox.get_attribute("checked") == "true"
        submit_button = self.wait_for_selector("#hgta_doTopSubmit")
        submit_button.click()
        self.screenshot("ucsc_table_browser_second_page")
        self.wait_for_selector("#hgta_doGalaxyQuery").click()
        # make sure we're back at Galaxy before we use the current session cookie to monitor the new hda.
        # It doesn't seem to me this should be needed but we're getting occasional failures about inaccessible
        # history I cannot explain otherwise. -John
        self.wait_for_masthead()
        self.history_panel_wait_for_hid_ok(1)
        # Make sure we're still logged in (xref https://github.com/galaxyproject/galaxy/issues/11374)
        self.components.masthead.logged_in_only.wait_for_visible()

import pytest
from selenium.webdriver.common.by import By

from galaxy.util.unittest_utils import skip_if_site_down
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class TestDataSource(SeleniumTestCase, UsesHistoryItemAssertions):
    ensure_registered = True
    framework_tool_and_types = True

    @pytest.mark.skip("Skipping UCSC table direct1 data source test, chromedriver fails captcha")
    @selenium_test
    @managed_history
    @skip_if_site_down("https://genome.ucsc.edu/cgi-bin/hgTables")
    def test_ucsc_table_direct1_data_source(self):
        self.home()
        self.datasource_tool_open("ucsc_table_direct1")
        self.screenshot("ucsc_table_browser_first_page")
        # only 4mb instead of 10 times that for human by default
        self.select_by_value((By.CSS_SELECTOR, "#org"), "Tree shrew")
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
        # Data source tools like UCSC can take longer to process external requests,
        # so we allow force refreshes to give the test more time to complete
        self.history_panel_wait_for_hid_ok(1, allowed_force_refreshes=2)
        # Make sure we're still logged in (xref https://github.com/galaxyproject/galaxy/issues/11374)
        self.components.masthead.logged_in_only.wait_for_visible()

    @selenium_test
    @managed_history
    def test_tool_runner_redirects_to_spa(self):
        """Data source tools redirect back to the Galaxy SPA after handing off control to the controller.

        Regression test for https://github.com/galaxyproject/galaxy/issues/22671: the new tab opened
        by an external data source app used to hit `/tool_runner?tool_id=...` and then JS-redirect
        back to `/`. After the mako removal the new tab was stranded on a static "ok" page; the
        controller now sends a 302 to `/?notification=tool-submitted` and the SPA surfaces a toast.
        """
        self.get("tool_runner?tool_id=test_data_source")
        # If the redirect is broken we land on a static page with no masthead.
        self.wait_for_masthead()
        # Confirm the SPA queued a toast from the notification query param.
        self.wait_for_selector_visible(".b-toast")
        self.screenshot("tool_runner_redirect_toast")

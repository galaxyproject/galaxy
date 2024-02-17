from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)

# Upload 11 datasets in order to exercise pagination in future
UPLOAD_DATA = {
    "bytes2": "m",
    "bytes3": "mo",
    "bytes4": "moo",
    "bytes5": "mooc",
    "bytes6": "mooco",
    "bytes7": "moocow",
    "bytes8": "moocow1",
    "bytes9": "moocow12",
    "bytes10": "moocow123",
    "bytes11": "moocow1234",
    "bytes12": "moocow1235",
}


class TestHistorySharing(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_history_storage(self):
        self.perform_upload_of_pasted_content(UPLOAD_DATA)
        self.history_panel_wait_for_hid_visible(11)
        self.wait_for_history()
        self.components.history_panel.storage_overview.wait_for_and_click()
        self.components.history_storage._.wait_for_visible()
        self.screenshot("history_storage")
        self.components.history_storage._.assert_no_axe_violations_with_impact_of_at_least("critical")

        self.home()
        self.components.masthead.storage_dashboard_link.wait_for_and_click()
        self.screenshot("storage_dashboard")
        self.components.storage_dashboard.free_space_link.wait_for_and_click()
        self.screenshot("storage_dashboard_manage_free_space_landing")
        self.assert_baseline_accessibility()

        self.home()
        self.components.masthead.storage_dashboard_link.wait_for_and_click()
        self.components.storage_dashboard.explore_usage_link.wait_for_and_click()
        self.screenshot("storage_dashboard_manage_explore_usage_landing")
        self.assert_baseline_accessibility()

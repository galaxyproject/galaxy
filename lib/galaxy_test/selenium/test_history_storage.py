from .framework import (
    managed_history,
    selenium_only,
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

UPLOAD_DATA_3 = {
    "small": "a",
    "medium": "aaaaa",
    "big": "aaaaaaaaaa",
}


class TestHistoryStorage(SeleniumTestCase):
    ensure_registered = True

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @managed_history
    def test_history_storage_accessibility(self):
        self.perform_upload_of_pasted_content(UPLOAD_DATA)
        self.history_panel_wait_for_hid_visible(11)
        self.wait_for_history()
        self.components.history_panel.storage_overview.wait_for_and_click()
        self.components.history_storage._.wait_for_visible()
        self.screenshot("history_storage")
        self.components.history_storage._.assert_no_axe_violations_with_impact_of_at_least("critical")

        # this is testing the global storage dashboard for the user - should be separated out
        # but I think it stuck them together so there is an existing history with data.
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

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @managed_history
    def test_delete_dataset_from_storage_view(self):
        """Test deleting a dataset from the history storage overview."""
        # Upload test data with different sizes
        self.perform_upload_of_pasted_content(UPLOAD_DATA_3)
        self.wait_for_history()

        # Navigate to history storage overview
        self.home()
        self.components.history_panel.storage_overview.wait_for_and_click()
        self.components.history_storage._.wait_for_visible()
        self.components.history_storage.top_datasets_by_size.wait_for_visible()

        # Click on the largest dataset
        self.components.history_storage.dataset_by_size(name="big").wait_for_and_click()
        self.screenshot("history_storage_active_dataset")

        # Delete the dataset
        self.components.history_storage.dataset_by_size_delete.wait_for_and_click()
        self.screenshot("history_storage_confirm_delete")
        self.components.history_storage.confirm_delete.wait_for_and_click()

        # Verify dataset is removed from storage view
        self.components.history_storage.dataset_by_size(name="big").wait_for_absent()
        self.screenshot("history_storage_post_delete")

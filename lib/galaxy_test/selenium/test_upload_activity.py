"""Integration coverage for the new Upload Activity."""

from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)
from .upload_activity_helpers import UsesUploadActivity


class TestUploadActivity(SeleniumTestCase, UsesUploadActivity, UsesHistoryItemAssertions):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_upload_with_metadata(self):
        """Upload file with custom metadata (name, extension, dbkey)"""
        (
            self.upload_context("local-file")
            .stage_local_file(self.get_filename("1.sam"), {"name": "my_data", "extension": "txt", "dbkey": "hg18"})
            .start()
        )
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_name(1, "my_data")
        self.assert_item_extension(1, "txt")
        self.assert_item_dbkey_displayed_as(1, "hg18")

    @selenium_test
    @managed_history
    def test_paste_content(self):
        """Upload pasted content with metadata"""
        (
            self.upload_context("paste-content")
            .stage_paste_content(
                "this is pasted from upload activity", {"name": "pasted_data", "extension": "txt", "dbkey": "apiMel3"}
            )
            .start()
        )
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_name(1, "pasted_data")
        self.assert_item_extension(1, "txt")
        self.assert_item_dbkey_displayed_as(1, "apiMel3")

    @selenium_test
    @managed_history
    def test_deferred_upload(self):
        """Upload with deferred status"""
        uploader = self.upload_context("paste-links")
        url = self.dataset_populator.base64_url_for_test_file("1.txt")
        item = uploader.stage_paste_link(url)
        item.set_deferred(True)
        uploader.start()
        self.history_panel_wait_for_hid_deferred(1)

    @selenium_test
    @managed_history
    def test_multiple_paste_links(self):
        """Upload from multiple URLs with individual metadata"""
        url1 = self.dataset_populator.base64_url_for_test_file("1.txt")
        url2 = self.dataset_populator.base64_url_for_test_file("2.txt")
        (
            self.upload_context("paste-links")
            .stage_paste_links(
                [
                    (url1, {"name": "link1", "extension": "tabular", "dbkey": "apiMel3"}),
                    (url2, {"name": "link2", "deferred": True}),
                ]
            )
            .start()
        )
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_name(1, "link1")
        self.assert_item_extension(1, "tabular")
        self.assert_item_dbkey_displayed_as(1, "apiMel3")

        self.history_panel_wait_for_hid_deferred(2)
        self.history_panel_click_item_title(hid=2, wait=True)
        self.assert_item_name(2, "link2")
        self.assert_item_dbkey_displayed_as(2, "?")

"""Integration coverage for the new Upload Activity."""

from galaxy_test.base.decorators import requires_admin
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

    @selenium_test
    @managed_history
    def test_composite_file_upload(self):
        """Upload a composite datatype by filling slots with mixed source modes."""
        slot_url = self.dataset_populator.base64_url_for_string("a")
        (
            self.upload_context("composite-file")
            .select_composite("velvet")
            .stage_composite_file_slot(slot=1, file_path=self.get_filename("1.txt"))
            .stage_composite_paste_slot(slot=2, content="b")
            .stage_composite_url_slot(slot=3, url=slot_url)
            .start()
        )
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_extension(1, "velvet")

    @selenium_test
    @managed_history
    def test_target_history_change(self):
        """Upload can be redirected to a non-current history via target selector."""
        source_history_id = self.current_history_id()
        target_history_id = self.dataset_populator.new_history(f"target_history_for_upload_{source_history_id}")
        try:
            context = self.upload_context("paste-content")
            context.stage_paste_content("upload to another history", {"name": "redirected_upload"})
            context.select_target_history(target_history_id)
            context.start()

            self.wait_for_history_to_have_hid(target_history_id, 1)
            target_contents = self.dataset_populator.get_history_contents(history_id=target_history_id)
            assert any(item.get("name") == "redirected_upload" for item in target_contents)

            source_contents = self.dataset_populator.get_history_contents(history_id=source_history_id)
            assert len(source_contents) == 0
        finally:
            self.api_delete(f"histories/{target_history_id}")


class TestUploadActivityDataLibrary(SeleniumTestCase, UsesUploadActivity, UsesHistoryItemAssertions):
    ensure_registered = True
    run_as_admin = True

    @selenium_test
    @managed_history
    @requires_admin
    def test_upload_from_data_library(self):
        """Upload Activity can import a selected dataset from a data library."""
        library_name = self._create_and_populate_library()

        self.upload_context("data-library").stage_data_library_dataset(library_name, "1.bed").start()

        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_name(1, "1.bed")

    def _create_and_populate_library(self):
        self.logout_if_needed()
        self.admin_login()
        library_name = self.create_new_library()
        self.populate_library_folder_from_import_dir(library_name, ["1.bed"])
        return library_name

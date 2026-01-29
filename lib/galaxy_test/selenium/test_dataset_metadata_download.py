from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)

FIRST_HID = 1


class TestHistoryDatasetState(SeleniumTestCase, UsesHistoryItemAssertions):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_dataset_metadata_download(self):
        self._prepare_dataset()
        item = self.history_panel_item_component(hid=FIRST_HID)
        item.download_button.wait_for_and_click()
        item.metadata_file_download(metadata_name="bam_index").wait_for_and_click()

    def _prepare_dataset(self):
        self.history_panel_create_new()
        self.perform_upload(self.get_filename("1.bam"))
        self.history_panel_wait_for_hid_ok(FIRST_HID)
        self.assert_item_name(FIRST_HID, "1.bam")

        # Expand HDA and wait for details to show up.
        return self.history_panel_click_item_title(hid=FIRST_HID, wait=True)

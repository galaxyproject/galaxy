from .framework import (
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class TestArchiveExplorer(SeleniumTestCase, UsesHistoryItemAssertions):
    @selenium_test
    def test_import_from_local_zip(self):
        self.login()
        self.ensure_empty_history()
        self.upload_start_click()
        self.explore_local_zip(self.get_filename("example-bag.zip"))
        self.expect_total_number_of_files_to_be(8)
        self.go_to_next_step()
        self.select_file_entry(file_path="test-bag-fetch-http/data/README.txt")
        self.go_to_next_step()
        self.expect_number_of_files_to_import(1)
        self.start_importing_files()
        self.expect_history_item_to_be_imported(hid=1, name="README.txt")

    # Helper methods
    # ------------------------------------------------------------------
    def ensure_empty_history(self):
        history_contents = self.history_contents()
        if len(history_contents) > 0:
            self.history_panel_create_new()

    def explore_local_zip(self, test_path: str):
        self.components.upload.explore_archive_button.wait_for_and_click()
        file_upload = self.wait_for_selector('input[type="file"]')
        file_upload.send_keys(test_path)

    def go_to_next_step(self):
        self.components.zip_import_wizard.wizard_next_button.wait_for_and_click()

    def start_importing_files(self):
        self.components.zip_import_wizard.wizard_import_button.wait_for_and_click()

    def select_file_entry(self, file_path: str):
        file_entry = self.components.zip_import_wizard.select_file(file_path=file_path)
        file_entry.wait_for_and_click()
        return file_entry

    def expect_total_number_of_files_to_be(self, file_count: int):
        zip_file_count_badge = self.components.zip_import_wizard.zip_file_count_badge
        badge_text = zip_file_count_badge.wait_for_text()
        assert badge_text.startswith(f"{file_count}")

    def expect_number_of_files_to_import(self, file_count: int):
        zip_file_count_badge = self.components.zip_import_wizard.selected_to_import_count_badge
        badge_text = zip_file_count_badge.wait_for_text()
        assert badge_text.startswith(f"{file_count}")

    def expect_history_item_to_be_imported(self, hid: int, name: str):
        self.history_panel_wait_for_hid_ok(hid)
        self.assert_item_name(hid, name)

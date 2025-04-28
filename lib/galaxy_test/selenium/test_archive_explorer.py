from selenium.webdriver.common.by import By

from galaxy.util.unittest_utils import skip_if_github_down
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

    @selenium_test
    @skip_if_github_down
    def test_import_from_remote_zip(self):
        remote_zip_url = "https://raw.githubusercontent.com/davelopez/ro-crate-zip-explorer/refs/heads/main/tests/test-data/rocrate-test.zip"
        self.login()
        self.ensure_empty_history()
        self.upload_start_click()
        self.explore_remote_zip(remote_zip_url)
        self.go_to_next_step()
        self.wait_for_loading_indicator_to_finish()
        self.expect_preview_title_to_be("Simple Workflow")
        self.go_to_next_step()
        self.select_file_entry(file_path="workflows/768c309887556fb5.gxwf.yml")
        self.select_file_entry(file_path="datasets/Trim_on_data_1_1690cb0a3211e932.txt")
        self.go_to_next_step()
        self.expect_number_of_workflows_to_import(1)
        self.expect_number_of_files_to_import(1)
        self.start_importing_files()
        self.expect_history_item_to_be_imported(hid=1, name="Trim on data 1")
        self.expect_workflow_to_be_imported_with_name(name="Simple Workflow")

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

    def explore_remote_zip(self, url: str):
        self.components.upload.explore_archive_button.wait_for_and_click()
        url_input = self.wait_for_selector('input[type="text"]#zip-url')
        url_input.send_keys(url)

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
        zip_file_count_badge = self.components.zip_import_wizard.selected_files_to_import_count_badge
        badge_text = zip_file_count_badge.wait_for_text()
        assert badge_text.startswith(f"{file_count}")

    def expect_number_of_workflows_to_import(self, file_count: int):
        zip_file_count_badge = self.components.zip_import_wizard.selected_workflows_to_import_count_badge
        badge_text = zip_file_count_badge.wait_for_text()
        assert badge_text.startswith(f"{file_count}")

    def expect_history_item_to_be_imported(self, hid: int, name: str):
        self.history_panel_wait_for_hid_ok(hid)
        self.assert_item_name(hid, name)

    def wait_for_loading_indicator_to_finish(self):
        loading_indicator = self.components.zip_import_wizard.loading_indicator
        loading_indicator.wait_for_present()
        loading_indicator.wait_for_absent()

    def expect_preview_title_to_be(self, title: str):
        title_text = self.components.zip_import_wizard.preview_title.wait_for_text()
        assert title_text == title

    def expect_workflow_to_be_imported_with_name(self, name: str):
        self.click_activity_workflow()
        workflow_cards = self.workflow_card_elements()
        assert len(workflow_cards) >= 1

        first_workflow_card = workflow_cards[0].find_element(By.CSS_SELECTOR, '[id^="g-card-title-"] a')
        assert f"{name} (imported from URL)" in first_workflow_card.text, first_workflow_card.text

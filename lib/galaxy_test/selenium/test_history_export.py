from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestHistoryExport(SeleniumTestCase):
    """Test history export wizard (requires Celery + STS enabled, the default)."""

    ensure_registered = True

    @selenium_test
    @managed_history
    def test_history_native_export_to_file(self):
        self.perform_upload_of_pasted_content("my cool content")
        self.history_panel_wait_for_hid_ok(1)

        self.home()
        self.click_history_option_export_to_file()
        history_export_tasks = self.components.history_export_tasks
        last_export_record = self.components.last_export_record

        self.screenshot("history_export_formats")
        # Step 1: Select export format (tar.gz)
        history_export_tasks.select_format(format="tar.gz").wait_for_and_click()
        history_export_tasks.next_button.wait_for_and_click()

        # Step 2: Select download destination
        history_export_tasks.select_destination(destination="download").wait_for_and_click()
        self.screenshot("history_export_native_destinations")
        history_export_tasks.next_button.wait_for_and_click()

        # Step 3: Complete the export
        self.screenshot("history_export_native_download_options")
        history_export_tasks.export_button.wait_for_and_click()

        # Wait for export to complete
        last_export_record.preparing_export_badge.wait_for_visible()
        self.screenshot("history_export_native_preparing_download")
        last_export_record.preparing_export_badge.wait_for_absent(wait_type=self.wait_types.DATABASE_OPERATION)
        last_export_record.download_btn.wait_for_visible()
        self.screenshot("history_export_native_download_ready")

    @selenium_test
    @managed_history
    def test_history_rocrate_export_to_file(self):
        self.perform_upload_of_pasted_content("my cool content")
        self.history_panel_wait_for_hid_ok(1)

        self.home()
        self.click_history_option_export_to_file()
        history_export_tasks = self.components.history_export_tasks
        last_export_record = self.components.last_export_record

        self.screenshot("history_export_formats")
        # Step 1: Select export format (rocrate)
        history_export_tasks.select_format(format="rocrate.zip").wait_for_and_click()
        history_export_tasks.next_button.wait_for_and_click()

        # Step 2: Select download destination
        history_export_tasks.select_destination(destination="download").wait_for_and_click()
        self.screenshot("history_export_rocrate_destinations")
        history_export_tasks.next_button.wait_for_and_click()

        # Step 3: Complete the export
        self.screenshot("history_export_rocrate_download_options")
        history_export_tasks.export_button.wait_for_and_click()

        # Wait for export to complete
        last_export_record.preparing_export_badge.wait_for_visible()
        self.screenshot("history_export_rocrate_preparing_download")
        last_export_record.preparing_export_badge.wait_for_absent(wait_type=self.wait_types.DATABASE_OPERATION)
        last_export_record.download_btn.wait_for_visible()
        self.screenshot("history_export_rocrate_download_ready")

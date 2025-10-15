from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestHistoryExport(SeleniumTestCase):
    """Test basic history export functionality.

    Tests the history export wizard workflow for exporting histories
    to different formats and destinations.
    """

    ensure_registered = True

    @selenium_test
    @managed_history
    def test_history_native_export_to_file(self):
        """Test exporting a history to a file in the native tar.gz format with temporary download link.

        This mirrors invocation export testing in test_workflow_run::test_workflow_export_file_native
        """
        # Upload test content to the history
        self.perform_upload_of_pasted_content("my cool content")
        self.history_panel_wait_for_hid_ok(1)

        # Navigate home and initiate history export
        self.home()
        self.click_history_option_export_to_file()
        history_export = self.components.history_export

        self.screenshot("history_export_formats")
        # Step 1: Select export format (tar.gz)
        history_export.export_output_format(type="tar.gz").wait_for_and_click()
        history_export.wizard_next_button.wait_for_and_click()

        # Step 2: Select download destination (temporary download link)
        download_option = history_export.export_destination(destination="download")
        download_option.wait_for_present()
        download_option.wait_for_and_click()
        self.screenshot("history_export_native_destinations")
        history_export.wizard_next_button.wait_for_and_click()

        # Step 3: Complete the export
        export_button = history_export.wizard_export_button
        export_button.wait_for_present()
        self.screenshot("history_export_native_download_options")
        export_button.wait_for_and_click()

        # Wait for export to be prepared
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("history_export_native_preparing_download")
        history_export.export_download_link.wait_for_present()
        self.screenshot("history_export_native_download_ready")

    @selenium_test
    @managed_history
    def test_history_rocrate_export_to_file(self):
        """Test exporting a history to an rocrate with temporary download link.

        This mirrors invocation export testing in test_workflow_run::test_workflow_export_file_rocrate
        """
        # Upload test content to the history
        self.perform_upload_of_pasted_content("my cool content")
        self.history_panel_wait_for_hid_ok(1)

        # Navigate home and initiate history export
        self.home()
        self.click_history_option_export_to_file()
        history_export = self.components.history_export

        self.screenshot("history_export_formats")
        # Step 1: Select export format (rocrate)
        history_export.export_output_format(type="rocrate").wait_for_and_click()
        history_export.wizard_next_button.wait_for_and_click()

        # Step 2: Select download destination (temporary download link)
        download_option = history_export.export_destination(destination="download")
        download_option.wait_for_present()
        download_option.wait_for_and_click()
        self.screenshot("history_export_rocrate_destinations")
        history_export.wizard_next_button.wait_for_and_click()

        # Step 3: Complete the export
        export_button = history_export.wizard_export_button
        export_button.wait_for_present()
        self.screenshot("history_export_rocrate_download_options")
        export_button.wait_for_and_click()

        # Wait for export to be prepared
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("history_export_rocrate_preparing_download")
        history_export.export_download_link.wait_for_present()
        self.screenshot("history_export_rocrate_download_ready")

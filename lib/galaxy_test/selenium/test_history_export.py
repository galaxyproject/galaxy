from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class HistoryExportTestCase(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_history_export(self):
        self.perform_upload_of_pasted_content("my cool content")
        self.history_panel_wait_for_hid_ok(1)

        self.click_history_option_export_to_file()

        history_export = self.components.history_export
        history_export.export_link.wait_for_and_click()
        history_export.running.wait_for_visible()
        history_export.running.wait_for_absent(wait_type=self.wait_types.JOB_COMPLETION)
        history_export.generated_export_link.wait_for_visible()
        history_export.copy_export_link.wait_for_visible()
        history_export.job_table.assert_absent_or_hidden()
        history_export.show_job_link.wait_for_and_click()
        history_export.job_table.wait_for_present()
        history_export.job_table_ok.wait_for_and_click()
        history_export.job_table.wait_for_absent()

        self.click_history_option_export_to_file()

        # this time the exported link is still there
        history_export.generated_export_link.wait_for_visible()
        history_export.export_link.assert_absent()

        self.perform_upload_of_pasted_content("my cool content part 2")
        self.history_panel_wait_for_hid_ok(2)

        self.click_history_option_export_to_file()

        # now we have a generated link and a link to update to the newest export
        history_export.generated_export_link.wait_for_visible()
        history_export.export_link.wait_for_visible()

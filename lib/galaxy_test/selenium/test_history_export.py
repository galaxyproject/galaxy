from .framework import (
    selenium_test,
    SeleniumTestCase
)


class HistoryExportTestCase(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_history_export(self):
        gx_selenium_context = self
        gx_selenium_context.perform_upload_of_pasted_content("my cool content")
        gx_selenium_context.history_panel_wait_for_hid_ok(1)
        gx_selenium_context.click_history_options()
        gx_selenium_context.components.history_panel.options_show_export_history_to_file.wait_for_and_click()
        history_export = gx_selenium_context.components.history_export
        history_export.export_link.wait_for_and_click()
        history_export.running.wait_for_visible()
        history_export.running.wait_for_absent(wait_type=gx_selenium_context.wait_types.JOB_COMPLETION)
        history_export.generated_export_link.wait_for_visible()
        history_export.copy_export_link.wait_for_visible()
        history_export.job_table.assert_absent_or_hidden()
        history_export.show_job_link.wait_for_and_click()
        history_export.job_table.wait_for_present()
        history_export.job_table_ok.wait_for_and_click()
        history_export.job_table.wait_for_absent()

        gx_selenium_context.click_history_options()
        gx_selenium_context.components.history_panel.options_show_export_history_to_file.wait_for_and_click()

        # this time the exported link is still there
        history_export.generated_export_link.wait_for_visible()
        history_export.export_link.assert_absent()

        gx_selenium_context.perform_upload_of_pasted_content("my cool content part 2")
        gx_selenium_context.history_panel_wait_for_hid_ok(2)

        gx_selenium_context.click_history_options()
        gx_selenium_context.components.history_panel.options_show_export_history_to_file.wait_for_and_click()

        # now we have a generated link and a link to update to the newest export
        history_export.generated_export_link.wait_for_visible()
        history_export.export_link.wait_for_visible()

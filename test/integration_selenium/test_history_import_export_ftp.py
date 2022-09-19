import os

from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class HistoryImportExportFtpSeleniumIntegrationTestCase(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        ftp_dir = cls.ftp_dir()
        os.makedirs(ftp_dir)
        config["ftp_upload_dir"] = ftp_dir
        config["ftp_upload_site"] = "ftp://ftp.galaxyproject.com"

    @classmethod
    def ftp_dir(cls):
        return cls.temp_config_dir("ftp")

    @selenium_test
    def test_history_import_export(self):
        email = self.get_logged_in_user()["email"]
        user_ftp_dir = os.path.join(self.ftp_dir(), email)
        os.makedirs(user_ftp_dir)

        gx_selenium_context = self
        gx_selenium_context.perform_upload_of_pasted_content("my cool content")
        gx_selenium_context.history_panel_wait_for_hid_ok(1)
        gx_selenium_context.click_history_options()
        gx_selenium_context.components.history_panel.options_show_export_history_to_file.wait_for_and_click()
        history_export = gx_selenium_context.components.history_export
        files_dialog = gx_selenium_context.components.files_dialog

        # we land on link version, but go to export to file
        history_export.export_link.wait_for_visible()
        history_export.tab_export_to_file.wait_for_and_click()
        history_export.export_link.wait_for_absent_or_hidden()
        history_export.directory_input.wait_for_and_click()

        # open directory by clicking on its name
        files_dialog.ftp_label.wait_for_and_click()
        self.components.upload.file_dialog_ok.wait_for_and_click()

        history_export.name_input.wait_for_and_send_keys("my_export.tar.gz")
        history_export.export_button.wait_for_and_click()

        history_export.running.wait_for_visible()
        history_export.running.wait_for_absent(wait_type=gx_selenium_context.wait_types.JOB_COMPLETION)
        history_export.success_message.wait_for_visible()

        gx_selenium_context.navigate_to_histories_page()
        gx_selenium_context.components.histories.import_button.wait_for_and_click()
        history_import = gx_selenium_context.components.history_import
        history_import.radio_button_remote_files.wait_for_and_click()
        files_dialog.ftp_label.wait_for_and_click()
        files_dialog.row(uri="gxftp://my_export.tar.gz").wait_for_and_click()

        history_import.import_button.wait_for_and_click()

        history_import.running.wait_for_visible()
        history_import.running.wait_for_absent(wait_type=gx_selenium_context.wait_types.JOB_COMPLETION)
        history_import.success_message.wait_for_visible()

        gx_selenium_context.navigate_to_histories_page()
        newest_history_name = gx_selenium_context.histories_get_history_names()[0]
        assert newest_history_name.startswith("imported from archive")

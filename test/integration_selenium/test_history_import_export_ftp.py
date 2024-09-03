import os

from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestHistoryImportExportFtpSeleniumIntegrationBase(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.setup_ftp_config(config)

    @classmethod
    def setup_ftp_config(cls, config):
        ftp_dir = cls.ftp_dir()
        os.makedirs(ftp_dir)
        config["ftp_upload_dir"] = ftp_dir
        config["ftp_upload_site"] = "ftp://ftp.galaxyproject.com"

    @classmethod
    def ftp_dir(cls):
        return cls.temp_config_dir("ftp")

    def create_user_ftp_dir(self):
        email = self.get_user_email()
        user_ftp_dir = os.path.join(self.ftp_dir(), email)
        os.makedirs(user_ftp_dir)

    def _export_to_ftp_with_filename(self, filename: str):
        self.components.history_export.directory_input.wait_for_and_click()
        self.components.files_dialog.ftp_label.wait_for_and_click()
        self.components.upload.file_dialog_ok.wait_for_and_click()
        self.components.history_export.name_input.wait_for_and_send_keys(filename)
        self.components.history_export.export_button.wait_for_and_click()


class TestHistoryImportExportFtpSeleniumIntegration(TestHistoryImportExportFtpSeleniumIntegrationBase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        # Setup only FTP without Celery
        cls.setup_ftp_config(config)

    @selenium_test
    def test_history_import_export(self):
        self.create_user_ftp_dir()

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

        self._export_to_ftp_with_filename("my_export.tar.gz")

        history_export.running.wait_for_visible()
        history_export.running.wait_for_absent(wait_type=gx_selenium_context.wait_types.JOB_COMPLETION)
        history_export.success_message.wait_for_visible()

        gx_selenium_context.navigate_to_histories_page()
        gx_selenium_context.components.histories.import_button.wait_for_and_click()
        history_import = gx_selenium_context.components.history_import
        history_import.radio_button_remote_files.wait_for_and_click()
        history_import.open_files_dialog.wait_for_and_click()
        files_dialog.ftp_label.wait_for_and_click()
        files_dialog.row(uri="gxftp://my_export.tar.gz").wait_for_and_click()

        history_import.import_button.wait_for_and_click()

        history_import.running.wait_for_visible()
        history_import.running.wait_for_absent(wait_type=gx_selenium_context.wait_types.JOB_COMPLETION)
        history_import.success_message.wait_for_visible()

        gx_selenium_context.navigate_to_histories_page()
        newest_history_name = gx_selenium_context.get_grid_entry_names("#histories-grid")[0]
        assert newest_history_name.startswith("imported from archive")


class TestHistoryImportExportFtpSeleniumIntegrationWithTasks(TestHistoryImportExportFtpSeleniumIntegrationBase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)

    @selenium_test
    def test_history_export_tracking(self):
        self.create_user_ftp_dir()

        self.perform_upload_of_pasted_content("my cool content")
        self.history_panel_wait_for_hid_ok(1)

        self.click_history_option_export_to_file()

        # Export to direct download link
        export_format = "rocrate.zip"
        history_export_tasks = self.components.history_export_tasks
        history_export_tasks.direct_download.wait_for_and_click()

        self._verify_last_export_record(expected_format=export_format, is_download=True)

        # Change export format
        export_format = "tar.gz"
        history_export_tasks.toggle_options_link.wait_for_and_click()
        history_export_tasks.export_format_selector.wait_for_visible()
        history_export_tasks.select_format(format=export_format).wait_for_and_click()
        history_export_tasks.toggle_options_link.wait_for_and_click()

        # Export to FTP file source
        history_export_tasks.file_source_tab.wait_for_present()
        history_export_tasks.file_source_tab.wait_for_and_click()
        self._export_to_ftp_with_filename("my_export.tar.gz")

        self._verify_last_export_record(expected_format=export_format)

    def _verify_last_export_record(
        self, expected_format: str, expect_up_to_date: bool = True, is_download: bool = False
    ):
        last_export_record = self.components.last_export_record
        last_export_record.preparing_export.wait_for_visible()
        last_export_record.preparing_export.wait_for_absent(wait_type=self.wait_types.DATABASE_OPERATION)

        last_export_record.details.wait_for_visible()
        format_element = last_export_record.export_format.wait_for_visible()
        assert format_element.text == expected_format

        if expect_up_to_date:
            last_export_record.up_to_date_icon.wait_for_visible()
        else:
            last_export_record.outdated_icon.wait_for_visible()

        if is_download:
            last_export_record.expiration_warning_icon.wait_for_visible()
            last_export_record.download_btn.wait_for_visible()
        else:
            last_export_record.reimport_btn.wait_for_visible()

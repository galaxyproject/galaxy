import os

from galaxy_test.selenium.upload_activity_helpers import UsesUploadActivity
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

FTP_UPLOAD_SITE = "ftp://ftp.galaxyproject.com"


class TestUploadFtpSeleniumIntegration(SeleniumIntegrationTestCase, UsesUploadActivity):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        ftp_dir = cls.ftp_dir()
        os.makedirs(ftp_dir)
        config["ftp_upload_dir"] = ftp_dir
        config["ftp_upload_site"] = FTP_UPLOAD_SITE

    @classmethod
    def ftp_dir(cls):
        return cls.temp_config_dir("ftp")

    def _upload_all(self, n):
        self.home()
        context = self.upload_context("remote-files")
        file_labels = [f"{i}.txt" for i in range(n)]
        context.stage_remote_files(source_label="FTP Directory", file_labels=file_labels)
        context.start()
        self.wait_for_history()
        for hid in range(1, n + 1):
            self.history_panel_wait_for_hid_ok(hid)
        contents = self.dataset_populator.get_history_contents(self.current_history_id())
        assert sorted(c["name"] for c in contents) == sorted(file_labels), contents

    def _create_ftp_dir(self):
        email = self.get_user_email()
        user_ftp_dir = os.path.join(self.ftp_dir(), email)
        os.makedirs(user_ftp_dir)
        return user_ftp_dir

    @selenium_test
    def test_ftp_directory_shows_upload_site(self) -> None:
        self._create_ftp_dir()
        self.home()
        self.upload_context("remote-files").open_remote_folder("FTP Directory")
        upload = self.components.upload_activity
        assert FTP_UPLOAD_SITE in upload.remote_files_ftp_help.wait_for_text()
        self.screenshot("upload_remote_files_ftp_help")
        upload.remote_files_breadcrumb_link(title="Sources").wait_for_and_click()
        upload.remote_files_browser_label(label="FTP Directory").wait_for_visible()
        upload.remote_files_ftp_help.wait_for_absent_or_hidden()

    @selenium_test
    def test_upload_simplest(self):
        user_ftp_dir = self._create_ftp_dir()
        file_path = os.path.join(user_ftp_dir, "0.txt")
        with open(file_path, "w") as f:
            f.write("Hello World!")
        self._upload_all(1)

    @selenium_test
    def test_upload_multiple(self):
        user_ftp_dir = self._create_ftp_dir()
        file_path = os.path.join(user_ftp_dir, "0.txt")
        with open(file_path, "w") as f:
            f.write("Hello World!")
        file_path = os.path.join(user_ftp_dir, "1.txt")
        with open(file_path, "w") as f:
            f.write("Hello Galaxy!")
        self._upload_all(2)

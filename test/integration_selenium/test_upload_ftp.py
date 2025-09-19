import os

from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestUploadFtpSeleniumIntegration(SeleniumIntegrationTestCase):
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

    def _upload_all(self, n):
        self.home()
        self.components.upload.start.wait_for_and_click()
        self.components.upload.file_dialog.wait_for_and_click()
        self.components.upload.file_source_selector(path="gxftp://").wait_for_and_click()
        for i in range(n):
            self.components.upload.file_source_selector(path=f"gxftp://{i}.txt").wait_for_and_click()
        self.components.upload.file_dialog_ok.wait_for_and_click()
        for i in range(n):
            self.components.upload.row(n=i).wait_for_visible()
        self.upload_start()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_history()

    def _create_ftp_dir(self):
        email = self.get_user_email()
        user_ftp_dir = os.path.join(self.ftp_dir(), email)
        os.makedirs(user_ftp_dir)
        return user_ftp_dir

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

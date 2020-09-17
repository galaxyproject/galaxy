import os

from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase
)


class UploadFtpSeleniumIntegrationTestCase(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        ftp_dir = cls.ftp_dir()
        os.makedirs(ftp_dir)
        config["ftp_upload_dir"] = ftp_dir
        config["ftp_upload_site"] = "ftp://ftp.galaxyproject.com"

    @classmethod
    def ftp_dir(cls):
        return cls.temp_config_dir("ftp")

    @selenium_test
    def test_upload_simplest(self):
        email = self.get_logged_in_user()["email"]
        user_ftp_dir = os.path.join(self.ftp_dir(), email)
        os.makedirs(user_ftp_dir)
        file_path = os.path.join(user_ftp_dir, "1.txt")
        with open(file_path, "w")as f:
            f.write("Hello World!")

        self.home()
        self.components.upload.start.wait_for_and_click()
        self.components.upload.ftp_add.wait_for_and_click()
        self.components.upload.ftp_popup.wait_for_visible()
        self.components.upload.ftp_items().all()[0].click()
        self.components.upload.ftp_close.wait_for_and_click()
        self.components.upload.row(n=0).wait_for_visible()
        self.upload_start()

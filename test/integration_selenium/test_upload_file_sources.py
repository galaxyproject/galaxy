from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class PosixFileSourceSeleniumIntegrationTestCase(PosixFileSourceSetup, SeleniumIntegrationTestCase):
    # For simplicity, otherwise need to setup a different file_sources_config_file
    requires_admin = True

    @selenium_test
    def test_upload_from_posix(self):
        self.admin_login()
        self.components.upload.start.wait_for_and_click()
        self.components.upload.ftp_add.wait_for_and_click()
        self.components.upload.file_source_selector(path="gxfiles://posix_test").wait_for_and_click()
        self.components.upload.file_source_selector(path="gxfiles://posix_test/a").wait_for_and_click()
        self.components.upload.file_dialog_ok.wait_for_and_click()
        self.upload_start()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_history()

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()

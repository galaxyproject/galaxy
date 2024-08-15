from typing import TYPE_CHECKING

from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator


class TestPosixFileSourceSeleniumIntegration(PosixFileSourceSetup, SeleniumIntegrationTestCase):
    dataset_populator: "SeleniumSessionDatasetPopulator"

    # For simplicity, otherwise need to setup a different file_sources_config_file
    run_as_admin = True

    @selenium_test
    def test_upload_from_posix(self):
        self.admin_login()
        self.components.upload.start.wait_for_and_click()
        self.components.upload.file_dialog.wait_for_and_click()
        self.components.upload.file_source_selector(path="gxfiles://posix_test").wait_for_and_click()
        self.components.upload.file_source_selector(path="gxfiles://posix_test/a").wait_for_and_click()
        self.components.upload.file_dialog_ok.wait_for_and_click()
        self.upload_start()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_history()

    @selenium_test
    def test_upload_from_posix_file_uri(self):
        self.admin_login()
        self.perform_upload_of_pasted_content(f"file://{self.root_dir}/a")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_history()

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()

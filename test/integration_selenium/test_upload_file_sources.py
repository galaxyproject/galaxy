from typing import TYPE_CHECKING

from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from galaxy_test.selenium.upload_activity_helpers import UsesUploadActivity
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)

if TYPE_CHECKING:
    from galaxy_test.selenium.framework import SeleniumSessionDatasetPopulator


class TestPosixFileSourceSeleniumIntegration(PosixFileSourceSetup, SeleniumIntegrationTestCase, UsesUploadActivity):
    dataset_populator: "SeleniumSessionDatasetPopulator"

    # For simplicity, otherwise need to setup a different file_sources_config_file
    run_as_admin = True

    @selenium_test
    def test_upload_from_posix(self):
        self.admin_login()
        self.upload_context("remote-files").stage_remote_file(
            source_label="Posix",
            file_label="a",
        ).start()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_history()

    @selenium_test
    def test_upload_from_posix_file_uri(self):
        self.admin_login()
        self.upload_context("paste-links").stage_paste_link(f"file://{self.root_dir}/a").start()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.wait_for_history()

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()

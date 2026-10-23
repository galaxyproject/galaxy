from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from galaxy_test.selenium.upload_activity_helpers import UsesUploadActivity
from .framework import (
    managed_history,
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestUploadActivityRemoteFiles(PosixFileSourceSetup, SeleniumIntegrationTestCase, UsesUploadActivity):
    run_as_admin = True
    ensure_registered = True

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()

    @selenium_test
    @managed_history
    def test_upload_from_remote_file_source(self):
        self.logout_if_needed()
        self.admin_login()
        self.upload_context("remote-files").stage_remote_file("Posix", "a").start()

        self.history_panel_wait_for_hid_ok(1)

    @selenium_test
    @managed_history
    def test_upload_from_remote_file_source_folder(self):
        self.logout_if_needed()
        self.admin_login()
        item = self.upload_context("remote-files").stage_remote_file("Posix", "b", path="subdir1")
        self.screenshot("upload_remote_files_subfolder_staged")
        item.start()

        self.history_panel_wait_for_hid_ok(1)
        assert self.dataset_populator.get_history_dataset_content(self.current_history_id(), hid=1) == "b\n"

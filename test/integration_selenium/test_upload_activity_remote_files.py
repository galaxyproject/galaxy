import os

from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from galaxy_test.selenium.upload_activity_helpers import UsesUploadActivity
from .framework import (
    managed_history,
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestUploadActivityRemoteFiles(PosixFileSourceSetup, SeleniumIntegrationTestCase, UsesUploadActivity):
    run_as_admin = True

    def setup_with_driver(self):
        super().setup_with_driver()
        self.admin_login()

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()

    @selenium_test
    @managed_history
    def test_upload_from_remote_file_source(self):
        self.upload_context("remote-files").stage_remote_file("Posix", "a").start()

        self.history_panel_wait_for_hid_ok(1)

    @selenium_test
    @managed_history
    def test_upload_from_remote_file_source_folder(self):
        item = self.upload_context("remote-files").stage_remote_file("Posix", "b", path="subdir1")
        self.screenshot("upload_remote_files_subfolder_staged")
        item.start()

        self.history_panel_wait_for_hid_ok(1)
        assert self.dataset_populator.get_history_dataset_content(self.current_history_id(), hid=1) == "b\n"

    @selenium_test
    def test_long_remote_file_name_stays_in_its_column(self):
        long_name = "m84091_230808_224522_s2.hifi_reads.bc2001.default_long_unbroken_run_name" * 2
        with open(os.path.join(self.root_dir, long_name), "w") as f:
            f.write("long\n")
        self.upload_context("remote-files").open_remote_folder("Posix")
        label = self.components.upload_activity.remote_files_browser_label(label=long_name).wait_for_visible()
        self.assert_label_within_its_column(label, "file name")
        self.screenshot("upload_remote_files_long_name_wrapped")

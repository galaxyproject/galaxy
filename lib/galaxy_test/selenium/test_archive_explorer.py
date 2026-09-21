from galaxy.util.unittest_utils import skip_if_github_down
from .framework import (
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)
from .upload_activity_helpers import UsesUploadActivity

REMOTE_ZIP_URL = "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/rocrate-test.zip"


class TestArchiveExplorer(SeleniumTestCase, UsesHistoryItemAssertions, UsesUploadActivity):
    @selenium_test
    def test_import_from_local_zip(self):
        self.login()
        self.ensure_empty_history()
        (
            self.upload_context("explore-zip")
            .explore_local_zip(self.get_filename("example-bag.zip"))
            .expect_total_files(8)
            .go_next()
            .select_file(file_path="test-bag-fetch-http/data/README.txt")
            .go_next()
            .expect_files_to_import(1)
            .start_import()
        )
        self.expect_history_item_to_be_imported(hid=1, name="README.txt")

    @selenium_test
    def test_explore_from_local_upload(self):
        self.login()
        self.ensure_empty_history()
        (
            self.upload_context("explore-zip")
            .explore_local_zip(self.get_filename("example-bag.zip"))
            .expect_total_files(8)
            .go_next()
            .select_file(file_path="test-bag-fetch-http/data/README.txt")
            .go_next()
            .expect_files_to_import(1)
            .start_import()
        )
        self.expect_history_item_to_be_imported(hid=1, name="README.txt")

    @selenium_test
    @skip_if_github_down
    def test_import_from_remote_zip(self):
        self.login()
        self.ensure_empty_history()
        (
            self.upload_context("explore-zip")
            .explore_remote_zip(REMOTE_ZIP_URL)
            .go_next()
            .wait_for_preview()
            .expect_preview_title("Simple Workflow")
            .go_next()
            .select_file(file_path="workflows/768c309887556fb5.gxwf.yml")
            .select_file(file_path="datasets/Trim_on_data_1_1690cb0a3211e932.txt")
            .go_next()
            .expect_workflows_to_import(1)
            .expect_files_to_import(1)
            .start_import()
        )
        self.expect_history_item_to_be_imported(hid=1, name="Trim on data 1")
        self.expect_workflow_to_be_imported_with_name(name="Simple Workflow")

    @selenium_test
    @skip_if_github_down
    def test_explore_remote_zip_paste_url(self):
        self.login()
        self.ensure_empty_history()
        (
            self.upload_context("explore-zip")
            .explore_remote_zip(REMOTE_ZIP_URL)
            .go_next()
            .wait_for_preview()
            .expect_preview_title("Simple Workflow")
        )

    @selenium_test
    def test_search_filters_files(self):
        self.login()
        self.ensure_empty_history()
        ctx = (
            self.upload_context("explore-zip")
            .explore_local_zip(self.get_filename("example-bag.zip"))
            .expect_total_files(8)
            .go_next()
        )

        visible_cards = ctx.get_visible_item_cards()
        assert len(visible_cards) == 8

        ctx.search_for("README")

        visible_cards = ctx.get_visible_item_cards()
        assert len(visible_cards) == 1

    @selenium_test
    def test_select_all_functionality(self):
        self.login()
        self.ensure_empty_history()
        (
            self.upload_context("explore-zip")
            .explore_local_zip(self.get_filename("example-bag.zip"))
            .expect_total_files(8)
            .go_next()
            .select_all_files()
            .go_next()
            .expect_files_to_import(8)
        )

    # Helper methods
    # ------------------------------------------------------------------
    def ensure_empty_history(self):
        history_contents = self.history_contents()
        if len(history_contents) > 0:
            self.history_panel_create_new()

    def expect_history_item_to_be_imported(self, hid: int, name: str):
        self.history_panel_wait_for_hid_ok(hid)
        self.assert_item_name(hid, name)

    def expect_workflow_to_be_imported_with_name(self, name: str):
        self.click_activity_workflow()
        self.components.workflows.workflow_cards.wait_for_visible()
        workflow_titles = self.components.workflows.workflow_card_title.all()
        assert len(workflow_titles) >= 1

        assert f"{name} (imported from URL)" in workflow_titles[0].text, workflow_titles[0].text

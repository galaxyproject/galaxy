"""Integration coverage for the new Upload Activity."""

from galaxy_test.base.decorators import (
    requires_admin,
    requires_new_history,
    requires_new_library,
)
from galaxy_test.base.populators import LibraryPopulator
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)
from .upload_activity_helpers import UsesUploadActivity


class TestUploadActivity(SeleniumTestCase, UsesUploadActivity, UsesHistoryItemAssertions):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_upload_with_metadata(self):
        """Upload file with custom metadata (name, extension, dbkey)"""
        (
            self.upload_context("local-file")
            .stage_local_file(self.get_filename("1.sam"), {"name": "my_data", "extension": "txt", "dbkey": "hg18"})
            .start()
        )
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_name(1, "my_data")
        self.assert_item_extension(1, "txt")
        self.assert_item_dbkey_displayed_as(1, "hg18")

    @selenium_test
    @managed_history
    def test_paste_content(self):
        """Upload pasted content with metadata"""
        (
            self.upload_context("paste-content")
            .stage_paste_content(
                "this is pasted from upload activity", {"name": "pasted_data", "extension": "txt", "dbkey": "apiMel3"}
            )
            .start()
        )
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_name(1, "pasted_data")
        self.assert_item_extension(1, "txt")
        self.assert_item_dbkey_displayed_as(1, "apiMel3")

    @selenium_test
    @managed_history
    def test_paste_content_converts_to_posix_lines_by_default(self):
        """Pasted content gets a trailing newline because POSIX line conversion is on by default"""
        self.upload_context("paste-content").stage_paste_content("a", {"extension": "txt"}).start()
        self.history_panel_wait_for_hid_ok(1)
        content = self.dataset_populator.get_history_dataset_content(self.current_history_id(), hid=1)
        assert content == "a\n"

    @selenium_test
    @managed_history
    def test_deferred_upload(self):
        """Upload with deferred status"""
        uploader = self.upload_context("paste-links")
        url = self.dataset_populator.base64_url_for_test_file("1.txt")
        item = uploader.stage_paste_link(url)
        item.set_deferred(True)
        uploader.start()
        self.history_panel_wait_for_hid_deferred(1)

    @selenium_test
    @managed_history
    def test_multiple_paste_links(self):
        """Upload from multiple URLs with individual metadata"""
        url1 = self.dataset_populator.base64_url_for_test_file("1.txt")
        url2 = self.dataset_populator.base64_url_for_test_file("2.txt")
        (
            self.upload_context("paste-links")
            .stage_paste_links(
                [
                    (url1, {"name": "link1", "extension": "tabular", "dbkey": "apiMel3"}),
                    (url2, {"name": "link2", "deferred": True}),
                ]
            )
            .start()
        )
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_name(1, "link1")
        self.assert_item_extension(1, "tabular")
        self.assert_item_dbkey_displayed_as(1, "apiMel3")

        self.history_panel_wait_for_hid_deferred(2)
        self.history_panel_click_item_title(hid=2, wait=True)
        self.assert_item_name(2, "link2")
        self.assert_item_dbkey_displayed_as(2, "?")

    @selenium_test
    @managed_history
    def test_composite_file_upload(self):
        """Upload a composite datatype by filling slots with mixed source modes."""
        slot_url = self.dataset_populator.base64_url_for_string("a")
        (
            self.upload_context("composite-file")
            .select_composite("velvet")
            .stage_composite_file_slot(slot=1, file_path=self.get_filename("1.txt"))
            .stage_composite_paste_slot(slot=2, content="b")
            .stage_composite_url_slot(slot=3, url=slot_url)
            .start()
        )
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_extension(1, "velvet")

    @selenium_test
    @requires_new_history
    def test_target_history_change(self):
        """Upload can be redirected to a non-current history via target selector."""
        with self.dataset_populator.test_history(require_new=True, name="target history") as target_history_id:
            with self.dataset_populator.test_history(require_new=True, name="current history") as current_history_id:
                self.home()
                context = self.upload_context("paste-content")
                context.stage_paste_content("upload to another history", {"name": "redirected_upload"})
                context.select_target_history(target_history_id)
                context.start()

                self.wait_for_history_to_have_hid(target_history_id, 1)
                target_contents = self.dataset_populator.get_history_contents(history_id=target_history_id)
                assert any(item.get("name") == "redirected_upload" for item in target_contents)

                source_contents = self.dataset_populator.get_history_contents(history_id=current_history_id)
                assert len(source_contents) == 0


class TestUploadActivityDataLibrary(SeleniumTestCase, UsesUploadActivity, UsesHistoryItemAssertions):
    ensure_registered = True
    run_as_admin = True

    @selenium_test
    @managed_history
    @requires_admin
    @requires_new_library
    def test_upload_from_data_library(self):
        """Upload Activity can import a selected dataset from a data library."""
        library_name = self._create_and_populate_library()

        item = self.upload_context("data-library").stage_data_library_dataset(library_name, "1.bed")
        self._screenshot_when_startable("upload_activity_data_library_staged")
        item.start()

        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.assert_item_name(1, "1.bed")

    @selenium_test
    @requires_admin
    @requires_new_library
    def test_upload_from_data_library_as_other_user(self):
        """A non-admin user can import a public library dataset uploaded by someone else."""
        library_name = self._create_and_populate_library()
        self.logout_if_needed()
        self.register()

        self.upload_context("data-library").stage_data_library_dataset(library_name, "1.bed").start()

        self.history_panel_wait_for_hid_ok(1)
        self.assert_item_name(1, "1.bed")
        self.screenshot("upload_activity_data_library_other_user_imported")

    @selenium_test
    @managed_history
    @requires_admin
    @requires_new_library
    def test_upload_list_from_data_library_to_target_history(self):
        """Select-all in a library subfolder builds a list in the picked target history, not the current one."""
        library_name = self._create_and_populate_library(["3.bed"], subfolders={"list folder": ["1.bed", "2.bed"]})
        current_history_id = self.current_history_id()
        # the long managed history name pushes the target history change link out of view
        self.dataset_populator.rename_history(current_history_id, "library list current")
        target_history_id = self.dataset_populator.new_history(name="library list target")
        # reload so the target history selector sees the new history
        self.home()

        context = self.upload_context("data-library")
        context.stage_data_library_datasets(
            library_name, ["1.bed", "2.bed"], folder_label="list folder", select_all=True
        )
        context.to_list("library list").select_target_history(target_history_id)
        # collection config is applied by start(), so this shows the staged items and target history
        self._screenshot_when_startable("upload_activity_data_library_target_history_staged")
        context.start()

        self._wait_on(
            lambda: any(
                c["history_content_type"] == "dataset_collection" for c in self.history_contents(target_history_id)
            ),
            "list in target history",
        )
        hdca = self.dataset_populator.get_history_collection_details(target_history_id)
        assert hdca["name"] == "library list"
        assert hdca["collection_type"] == "list"
        assert [e["element_identifier"] for e in hdca["elements"]] == ["1.bed", "2.bed"]
        assert self.history_contents(current_history_id) == []

    def _screenshot_when_startable(self, label):
        self.components.upload_activity.start_button_enabled.wait_for_visible()
        # let the button's enable color transition finish so the screenshot doesn't show it greyed out
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot(label)

    def _create_and_populate_library(self, filenames=("1.bed",), subfolders=None):
        self.logout_if_needed()
        self.admin_login()
        library_populator = LibraryPopulator(self.api_interactor_for_logged_in_user())
        library = library_populator.new_library(self._get_random_name(prefix="upload_library"))
        items = self._library_items(filenames)
        for folder_name, folder_filenames in (subfolders or {}).items():
            items.append({"name": folder_name, "elements": self._library_items(folder_filenames)})
        library_populator.fetch_to_folder(library["root_folder_id"], items)
        # library uploads are restricted to the uploader's private role
        for entry in library_populator.get_library_contents(library["id"]):
            if entry["type"] == "file":
                library_populator.remove_library_dataset_restrictions(entry["id"])
        return library["name"]

    def _library_items(self, filenames):
        items = []
        for filename in filenames:
            with open(self.get_filename(filename)) as f:
                items.append({"src": "pasted", "paste_content": f.read(), "name": filename, "ext": "bed"})
        return items

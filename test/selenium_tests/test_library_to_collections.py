import unittest

from .framework import (
    selenium_test,
    SeleniumTestCase,
)


@unittest.skip
class LibraryToCollectionsTestCase(SeleniumTestCase):

    requires_admin = True

    @selenium_test
    def test_list_creation(self):
        self.admin_login()
        self.perform_upload(self.get_filename("1.bed"))
        self.history_panel_wait_for_hid_ok(1, allowed_force_refreshes=1)
        self.perform_upload(self.get_filename("2.bed"))
        self.history_panel_wait_for_hid_ok(2, allowed_force_refreshes=1)

        self.name = self._get_random_name(prefix="testcontents")

        self.libraries_open()
        self.libraries_index_create(self.name)
        self.libraries_open_with_name(self.name)

        self.libraries_dataset_import_from_history()
        self.libraries_dataset_import_from_history_select(["1.bed", "2.bed"])
        self.sleep_for(self.wait_types.UX_RENDER)
        self.libraries_dataset_import_from_history_click_ok()

        self.home()

        self.history_panel_create_new_with_name("new_history_for_library_list")
        self.libraries_open_with_name(self.name)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.components.libraries.folder.select_all.wait_for_and_click()
        self.components.libraries.folder.add_to_history.wait_for_and_click()
        self.screenshot("libraries_add_to_history_menu")
        self.components.libraries.folder.add_to_history_collection.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("libraries_to_collection_landing")
        self.components.libraries.folder.import_datasets_ok_button.wait_for_and_click()

        self.collection_builder_set_name("my cool list")
        self.collection_builder_create()
        self.home()
        self.history_panel_wait_for_hid_ok(3)

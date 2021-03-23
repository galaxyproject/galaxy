from .framework import (
    selenium_test,
    SeleniumTestCase,
    UsesLibraryAssertions
)


class LibraryToCollectionsTestCase(SeleniumTestCase, UsesLibraryAssertions):

    requires_admin = True

    @selenium_test
    def test_collection_export(self):
        self.prepare_library_for_data_export()
        self.screenshot("libraries_to_collection_landing")
        self.components.libraries.folder.import_datasets_ok_button.wait_for_and_click()
        self.build_collection_and_assert()

    @selenium_test
    def test_pair_export(self):
        self.prepare_library_for_data_export()
        self.components.libraries.folder.export_to_history_options.wait_for_and_click()
        self.components.libraries.folder.export_to_history_paired_option(collection_option="paired").wait_for_and_click()
        self.screenshot("libraries_to_pared_collection_landing")
        self.components.libraries.folder.import_datasets_ok_button.wait_for_and_click()
        self.build_collection_and_assert()

    def prepare_library_for_data_export(self):
        self.navigate_to_new_library()
        self.assert_num_displayed_items_is(0)
        self.populate_library_folder_from_import_dir(self.name, ["1.bam", "1.bed"])

        self.components.libraries.folder.select_dataset(rowindex=1).wait_for_and_click()
        self.components.libraries.folder.select_dataset(rowindex=2).wait_for_and_click()
        self.components.libraries.folder.add_to_history.wait_for_and_click()
        self.screenshot("libraries_add_to_history_menu")
        self.components.libraries.folder.add_to_history_collection.wait_for_and_click()

    def build_collection_and_assert(self):
        self.collection_builder_set_name(self._get_random_name())
        self.collection_builder_create()
        self.home()
        self.history_panel_wait_for_hid_ok(3)



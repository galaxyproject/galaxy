from .framework import (
    selenium_test,
    SeleniumTestCase,
    UsesLibraryAssertions,
)


class LibraryToCollectionsTestCase(SeleniumTestCase, UsesLibraryAssertions):

    requires_admin = True

    @selenium_test
    def test_library_collection_export_new_history(self):
        self.collection_export(is_new_history=True)

    @selenium_test
    def test_library_collection_export(self):
        self.collection_export()

    @selenium_test
    def test_library_pair_export_new_history(self):
        self.collection_export(is_new_history=True, collection_option="paired")

    @selenium_test
    def test_library_pair_export(self):
        self.collection_export(collection_option="paired")

    @selenium_test
    def test_export_pairs_list_new_history(self):
        self.list_of_pairs_export(is_new_history=True)

    @selenium_test
    def test_export_pairs_list(self):
        self.list_of_pairs_export()

    def prepare_library_for_data_export(self, files_to_import, history_name=None):
        self.create_new_library()
        self.home()
        self.history_panel_create_new()
        self.libraries_open_with_name(self.name)
        self.assert_num_displayed_items_is(0)
        self.populate_library_folder_from_import_dir(self.name, files_to_import)
        for i in range(len(files_to_import)):
            self.components.libraries.folder.select_dataset(rowindex=i + 1).wait_for_and_click()
        self.components.libraries.folder.add_to_history.wait_for_and_click()
        self.components.libraries.folder.add_to_history_collection.wait_for_and_click()
        if history_name is not None:
            self.components.libraries.folder.export_to_history_new_history.wait_for_and_send_keys(history_name)

    def build_collection_and_assert(self):
        self.collection_builder_set_name(self._get_random_name())
        self.collection_builder_create()
        self.home()
        self.history_panel_wait_for_hid_ok(3)

    def collection_export(self, is_new_history=False, collection_option=None):
        random_name = self._get_random_name()
        self.prepare_library_for_data_export(["1.bam", "1.bed"], random_name if is_new_history else None)
        self.components.libraries.folder.export_to_history_options.wait_for_and_click()

        if collection_option is not None:
            self.components.libraries.folder.export_to_history_paired_option(
                collection_option=collection_option
            ).wait_for_and_click()
        self.screenshot(f"libraries_to_collection_landing_is_new_history={is_new_history}")
        self.components.libraries.folder.import_datasets_ok_button.wait_for_and_click()
        self.build_collection_and_assert()
        if is_new_history:
            assert self.history_panel_name_element().text == random_name

    def list_of_pairs_export(self, is_new_history=False):
        history_name = self._get_random_name()
        self.prepare_library_for_data_export(
            ["bam_from_sam.bam", "asian_chars_1.txt", "1.bam", "1.bed"], history_name if is_new_history else None
        )
        self.components.libraries.folder.export_to_history_options.wait_for_and_click()
        self.components.libraries.folder.export_to_history_paired_option(
            collection_option="list:paired"
        ).wait_for_and_click()
        self.screenshot(f"test_export_pairs_list={is_new_history}")
        self.components.libraries.folder.import_datasets_ok_button.wait_for_and_click()
        self.components.libraries.folder.clear_filters.wait_for_and_click()
        self.collection_builder_click_paired_item("forward", 0)
        self.collection_builder_click_paired_item("reverse", 1)
        self.components.libraries.folder.export_to_history_collection_name.wait_for_and_send_keys(
            self._get_random_name()
        )
        self.collection_builder_create()
        self.home()
        self.history_panel_wait_for_hid_ok(3)
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_wait_for_hid_hidden(2)
        if is_new_history:
            assert self.history_panel_name_element().text == history_name

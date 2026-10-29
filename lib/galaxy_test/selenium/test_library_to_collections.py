from galaxy_test.base.decorators import requires_admin
from .framework import (
    selenium_test,
    SeleniumTestCase,
    UsesLibraryAssertions,
)


class TestLibraryToCollections(SeleniumTestCase, UsesLibraryAssertions):
    run_as_admin = True

    @selenium_test
    @requires_admin
    def test_library_collection_export_new_history(self):
        self.collection_export(is_new_history=True)

    @selenium_test
    @requires_admin
    def test_library_collection_export(self):
        self.collection_export()

    @selenium_test
    @requires_admin
    def test_library_pair_export_new_history(self):
        self.collection_export(is_new_history=True, collection_option="paired")

    @selenium_test
    @requires_admin
    def test_library_pair_export(self):
        self.collection_export(collection_option="paired")

    @selenium_test
    @requires_admin
    def test_export_pairs_list_new_history(self):
        self.list_of_pairs_export(is_new_history=True)

    @selenium_test
    @requires_admin
    def test_export_pairs_list(self):
        self.list_of_pairs_export()

    @selenium_test
    @requires_admin
    def test_library_collection_export_to_selected_history(self):
        self.admin_login()
        target_history_id = self.dataset_populator.new_history(name=self._get_random_name())
        self.prepare_library_for_data_export(["1.bam", "1.bed"], history_id=target_history_id)
        self.wait_for_fade_in(self.components.libraries.folder.add_to_history_modal)
        self.screenshot("libraries_to_collection_selected_history")
        other_history_id = self.current_history_id()
        self.components.libraries.folder.add_to_history_as_collection.wait_for_and_click()
        collection_name = self._get_random_name()
        self.collection_builder_set_name(collection_name)
        self.collection_builder_create()
        self._wait_on(
            lambda: collection_name in self.history_collection_names(target_history_id),
            "the list in the selected history",
        )
        assert self.history_collection_names(other_history_id) == []
        self.wait_for_current_history_id(target_history_id)

    def prepare_library_for_data_export(self, files_to_import, history_name=None, history_id=None):
        self.create_new_library()
        self.home()
        self.history_panel_create_new()
        self.libraries_open_with_name(self.name)
        self.assert_num_displayed_items_is(0)
        self.populate_library_folder_from_import_dir(self.name, files_to_import)
        self.libraries_folder_select_datasets(files_to_import)
        self.components.libraries.folder.add_to_history.wait_for_and_click()
        self.components.libraries.folder.add_to_history_collection.wait_for_and_click()
        if history_id is not None:
            self.components.libraries.folder.export_to_history_history_select.select_by_value(history_id)
        if history_name is not None:
            self.components.libraries.folder.export_to_history_new_history.wait_for_and_send_keys(history_name)

    def build_collection_and_assert(self):
        self.collection_builder_set_name(self._get_random_name())
        self.collection_builder_create()
        self.home()
        self.history_panel_wait_for_hid_ok(3)

    def collection_export(self, is_new_history=False, collection_option=None):
        random_name = self._get_random_name()
        self.admin_login()
        self.prepare_library_for_data_export(["1.bam", "1.bed"], random_name if is_new_history else None)
        if collection_option is not None:
            self.select_by_value(
                self.navigation.libraries.folder.selectors.export_to_history_options, collection_option
            )
        self.wait_for_fade_in(self.components.libraries.folder.add_to_history_modal)
        self.screenshot(f"libraries_to_collection_landing_is_new_history={is_new_history}")
        self.components.libraries.folder.add_to_history_as_collection.wait_for_and_click()
        self.build_collection_and_assert()
        if is_new_history:
            assert self.history_panel_name_element().text == random_name

    def list_of_pairs_export(self, is_new_history=False):
        history_name = self._get_random_name()
        self.admin_login()
        self.prepare_library_for_data_export(
            ["bam_from_sam.bam", "asian_chars_1.txt", "1.bam", "1.bed"], history_name if is_new_history else None
        )
        self.select_by_value(self.navigation.libraries.folder.selectors.export_to_history_options, "list:paired")
        self.wait_for_fade_in(self.components.libraries.folder.add_to_history_modal)
        self.screenshot(f"test_export_pairs_list={is_new_history}")
        self.components.libraries.folder.add_to_history_as_collection.wait_for_and_click()
        self.collection_builder_pair_rows(0, 1)
        self.components.collection_builders.list_wizard.dismiss_unmatched.wait_for_and_click()
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

from .framework import SeleniumTestCase
from .framework import selenium_test


class CollectionBuildersTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_build_list_simple(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_multi_operations_show()
        self.history_panel_muli_operation_select_hid(1)
        self.history_panel_multi_operation_action_click("Build Dataset List")

        self.collection_builder_set_name("my cool list")

        self.collection_builder_create()
        self.history_panel_wait_for_hid_ok(2)

    @selenium_test
    def test_build_list_and_hide_items(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_multi_operations_show()
        self.history_panel_muli_operation_select_hid(1)
        self.history_panel_multi_operation_action_click("Build Dataset List")

        self.collection_builder_hide_originals()
        self.collection_builder_set_name("my cool list")

        self.collection_builder_create()
        self.history_panel_wait_for_hid_ok(2)
        self.history_panel_refresh_click()
        self.history_panel_wait_for_hid_hidden(1)

    @selenium_test
    def test_build_pair_simple(self):
        self.perform_upload(self.get_filename("1.tabular"))
        self.perform_upload(self.get_filename("2.tabular"))
        self.history_panel_wait_for_hid_visible(1)
        self.history_panel_wait_for_hid_visible(2)
        self.history_panel_multi_operations_show()
        self.history_panel_muli_operation_select_hid(1)
        self.history_panel_muli_operation_select_hid(2)
        self.history_panel_multi_operation_action_click("Build Dataset Pair")
        self.collection_builder_set_name("my awesome pair")

        self.collection_builder_create()
        self.history_panel_wait_for_hid_ok(3)

    @selenium_test
    def test_build_paired_list_simple(self):
        self.perform_upload(self.get_filename("1.tabular"))
        self.perform_upload(self.get_filename("2.tabular"))
        self.history_panel_wait_for_hid_visible(1)
        self.history_panel_wait_for_hid_visible(2)
        self.history_panel_multi_operations_show()
        self.history_panel_muli_operation_select_hid(1)
        self.history_panel_muli_operation_select_hid(2)
        self.history_panel_multi_operation_action_click("Build List of Dataset Pairs")

        self.collection_builder_clear_filters()
        self.collection_builder_click_paired_item("forward", 0)
        self.collection_builder_click_paired_item("reverse", 1)
        self.collection_builder_set_name("my awesome paired list")

        self.collection_builder_create()
        self.history_panel_wait_for_hid_ok(3)

    @selenium_test
    def test_build_paired_list_hide_original(self):
        self.perform_upload(self.get_filename("1.tabular"))
        self.perform_upload(self.get_filename("2.tabular"))
        self.history_panel_wait_for_hid_visible(1)
        self.history_panel_wait_for_hid_visible(2)
        self.history_panel_multi_operations_show()
        self.history_panel_muli_operation_select_hid(1)
        self.history_panel_muli_operation_select_hid(2)
        self.history_panel_multi_operation_action_click("Build List of Dataset Pairs")

        clear_filter_link = self.wait_for_selector_visible("a.clear-filters-link")
        clear_filter_link.click()

        forward_column = self.wait_for_selector_visible(".forward-column .column-datasets")
        first_datset_forward = forward_column.find_elements_by_css_selector("li")[0]
        first_datset_forward.click()

        reverse_column = self.wait_for_selector_visible(".reverse-column .column-datasets")
        second_dataset_reverse = reverse_column.find_elements_by_css_selector("li")[1]
        second_dataset_reverse.click()

        self.collection_builder_hide_originals()
        self.collection_builder_set_name("my awesome paired list")

        self.collection_builder_create()
        self.history_panel_wait_for_hid_ok(3)
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_wait_for_hid_hidden(2)

from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestCollectionBuilders(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_build_list_simple_hidden(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self._wait_for_and_select([1])
        self._collection_dropdown("build list")
        self.collection_builder_set_name("my cool list")
        self.screenshot("collection_builder_list")
        self.collection_builder_create()
        self._wait_for_hid_visible(3)

    @selenium_test
    @managed_history
    def test_build_list_and_show_items(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self._wait_for_and_select([1])
        self._collection_dropdown("build list")

        # this toggles the checkbox to not hide originals
        self.collection_builder_hide_originals()
        self.collection_builder_set_name("my cool list")
        self.collection_builder_create()
        self._wait_for_hid_visible(3)

    @selenium_test
    @managed_history
    def test_build_paired_list_simple(self):
        self.perform_upload(self.get_filename("1.tabular"))
        self.perform_upload(self.get_filename("2.tabular"))
        self._wait_for_and_select([1, 2])
        self._collection_dropdown("build list of pairs")
        self.collection_builder_clear_filters()
        self.collection_builder_click_paired_item("forward", 0)
        self.collection_builder_click_paired_item("reverse", 1)
        self.collection_builder_set_name("my awesome paired list")
        self.screenshot("collection_builder_paired_list")
        self.collection_builder_create()
        self._wait_for_hid_visible(5)
        # switch to hidden filters to see the hidden datasets appear
        self._show_hidden_content()
        self._wait_for_hid_visible(1)
        self._wait_for_hid_visible(2)
        self._wait_for_hid_visible(3)
        self._wait_for_hid_visible(4)

    @selenium_test
    @managed_history
    def test_build_paired_list_show_original(self):
        self.perform_upload(self.get_filename("1.tabular"))
        self.perform_upload(self.get_filename("2.tabular"))
        self._wait_for_and_select([1, 2])
        self._collection_dropdown("build list of pairs")
        collection_builders = self.components.collection_builders
        collection_builders.clear_filters.wait_for_and_click()
        forward_column = collection_builders.forward_datasets.wait_for_visible()
        first_datset_forward = forward_column.find_elements(self.by.CSS_SELECTOR, "li")[0]
        first_datset_forward.click()
        reverse_column = collection_builders.reverse_datasets.wait_for_visible()
        second_dataset_reverse = reverse_column.find_elements(self.by.CSS_SELECTOR, "li")[1]
        second_dataset_reverse.click()
        self.collection_builder_hide_originals()
        self.collection_builder_set_name("my awesome paired list")
        self.collection_builder_create()
        self._wait_for_hid_visible(5)
        self._wait_for_hid_visible(1)
        self._wait_for_hid_visible(2)
        self._show_hidden_content()
        self._wait_for_hid_visible(3)
        self._wait_for_hid_visible(4)

    @selenium_test
    @managed_history
    def test_build_simple_list_via_rules_hidden(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self._wait_for_and_select([1])
        self._collection_dropdown("build collection from rules")
        self.collection_builder_set_name("my cool list")
        self.screenshot("collection_builder_rules_list")
        self.collection_builder_create()
        self._wait_for_hid_visible(3)
        self._show_hidden_content()
        self._wait_for_hid_visible(1)
        self._wait_for_hid_visible(2)

    def _wait_for_hid_visible(self, hid, state="ok"):
        # takes a little while for these things to upload and end up in the history
        timeout = self.wait_length(self.wait_types.JOB_COMPLETION)
        row_selector = self.content_item_by_attributes(hid=hid, state=state)
        self.wait_for_visible(row_selector, timeout=timeout)

    def _collection_dropdown(self, option_description):
        return self.use_bootstrap_dropdown(option=option_description, menu="selected content menu")

    def _wait_for_and_select(self, hids):
        """
        Waits for uploads to pass through queued, running, ok. Not all the states are not guaranteed
        depending on how fast the upload goes compared to the history polling updates, it might just
        skip to the end for a really fast upload
        """
        for hid in hids:
            self.history_panel_wait_for_hid_ok(hid)
        self.history_panel_multi_operations_show()
        for hid in hids:
            self.history_panel_muli_operation_select_hid(hid)

    def _show_hidden_content(self):
        """Switches the hidden filter toggle on"""
        self.sleep_for(self.wait_types.UX_RENDER)
        filter_element = self.history_element(
            attribute_value="filter text input", scope=".content-operations-filters"
        ).wait_for_and_click()
        filter_element.send_keys("visible:false")
        self.sleep_for(self.wait_types.UX_RENDER)

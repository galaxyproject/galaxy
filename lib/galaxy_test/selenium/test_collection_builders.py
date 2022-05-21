from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class CollectionBuildersTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_build_list_simple_hidden(self):
        self.perform_upload(self.get_filename("1.fasta"))

        self._wait_for_and_select([1])

        if self.is_beta_history():
            self._collection_dropdown("build list")
        else:
            self.history_panel_multi_operation_action_click(
                self.navigation.history_panel.multi_operations.labels.build_list
            )

        self.collection_builder_set_name("my cool list")
        self.screenshot("collection_builder_list")
        self.collection_builder_create()
        self._wait_for_hid_visible(2)

    @selenium_test
    def test_build_list_and_show_items(self):
        self.perform_upload(self.get_filename("1.fasta"))

        self._wait_for_and_select([1])

        if self.is_beta_history():
            self._collection_dropdown("build list")
        else:
            self.history_panel_multi_operation_action_click(
                self.navigation.history_panel.multi_operations.labels.build_list
            )

        # this toggles the checkbox to not hide originals
        self.collection_builder_hide_originals()
        self.collection_builder_set_name("my cool list")
        self.collection_builder_create()
        self.home()  # this shouldn't be necessary, and it isn't with a real browser.
        self._wait_for_hid_visible(3)

    @selenium_test
    def test_build_pair_simple_hidden(self):
        self.perform_upload(self.get_filename("1.tabular"))
        self.perform_upload(self.get_filename("2.tabular"))

        self._wait_for_and_select([1, 2])

        if self.is_beta_history():
            self._collection_dropdown("build pair")
        else:
            self.history_panel_multi_operation_action_click(
                self.navigation.history_panel.multi_operations.labels.build_pair
            )

        self.collection_builder_set_name("my awesome pair")
        self.screenshot("collection_builder_pair")
        self.collection_builder_create()
        self._wait_for_hid_visible(3)

    @selenium_test
    def test_build_paired_list_simple(self):
        self.perform_upload(self.get_filename("1.tabular"))
        self.perform_upload(self.get_filename("2.tabular"))

        # self.home()
        self._wait_for_and_select([1, 2])

        if self.is_beta_history():
            self._collection_dropdown("build list of pairs")
        else:
            self.history_panel_multi_operation_action_click(
                self.navigation.history_panel.multi_operations.labels.build_list_pairs
            )

        self.collection_builder_clear_filters()
        self.collection_builder_click_paired_item("forward", 0)
        self.collection_builder_click_paired_item("reverse", 1)
        self.collection_builder_set_name("my awesome paired list")
        self.screenshot("collection_builder_paired_list")
        self.collection_builder_create()

        if self.is_beta_history():
            self._wait_for_hid_visible(3)
            # switch to hidden filters to see the hidden datasets appear
            self._show_hidden_content()
            self._wait_for_hid_visible(1)
            self._wait_for_hid_visible(2)
        else:
            self.history_panel_wait_for_hid_ok(3)
            self.history_panel_wait_for_hid_hidden(1)
            self.history_panel_wait_for_hid_hidden(2)

    @selenium_test
    def test_build_paired_list_show_original(self):
        self.perform_upload(self.get_filename("1.tabular"))
        self.perform_upload(self.get_filename("2.tabular"))

        # self.home()  # should not be necessary, chromedriver fails without it though
        self._wait_for_and_select([1, 2])

        if self.is_beta_history():
            self._collection_dropdown("build list of pairs")
        else:
            self.history_panel_multi_operation_action_click(
                self.navigation.history_panel.multi_operations.labels.build_list_pairs
            )

        self.wait_for_and_click(self.navigation.collection_builders.selectors.clear_filters)

        forward_column = self.wait_for_visible(self.navigation.collection_builders.selectors.forward_datasets)
        first_datset_forward = forward_column.find_elements_by_css_selector("li")[0]
        first_datset_forward.click()

        reverse_column = self.wait_for_visible(self.navigation.collection_builders.selectors.reverse_datasets)
        second_dataset_reverse = reverse_column.find_elements_by_css_selector("li")[1]
        second_dataset_reverse.click()

        self.collection_builder_hide_originals()
        self.collection_builder_set_name("my awesome paired list")
        self.collection_builder_create()

        if self.is_beta_history():
            self._wait_for_hid_visible(5)
            self._wait_for_hid_visible(1)
            self._wait_for_hid_visible(2)
            self._show_hidden_content()
            self._wait_for_hid_visible(3)
            self._wait_for_hid_visible(4)
        else:
            self.history_panel_wait_for_hid_ok(5)
            self.history_panel_refresh_click()
            self.history_panel_wait_for_hid_ok(1)
            self.history_panel_wait_for_hid_ok(2)
            self.history_panel_wait_for_hid_hidden(3)
            self.history_panel_wait_for_hid_hidden(4)

    @selenium_test
    def test_build_simple_list_via_rules_hidden(self):
        self.perform_upload(self.get_filename("1.fasta"))

        self._wait_for_and_select([1])

        if self.is_beta_history():
            self._collection_dropdown("build collection from rules")
        else:
            self.history_panel_multi_operation_action_click(
                self.navigation.history_panel.multi_operations.labels.build_from_rules
            )

        self.collection_builder_set_name("my cool list")
        self.screenshot("collection_builder_rules_list")
        self.collection_builder_create()

        self._wait_for_hid_visible(2)

        if self.is_beta_history():
            self._show_hidden_content()
            self._wait_for_hid_visible(1)
        else:
            self.history_panel_wait_for_hid_hidden(1)

    def _wait_for_hid_visible(self, hid, state="ok"):
        if self.is_beta_history():
            # takes a little while for these things to upload and end up in the history
            timeout = self.wait_length(self.wait_types.JOB_COMPLETION)
            row_selector = self.content_item_by_attributes(hid=hid, state=state)
            self.wait_for_visible(row_selector, timeout=timeout)
        else:
            self.history_panel_wait_for_hid_visible(hid, allowed_force_refreshes=1)

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
        """Switches the beta hidden filter toggle on"""
        self.sleep_for(self.wait_types.UX_RENDER)
        filter_element = self.beta_history_element("filter text input").wait_for_and_click()
        filter_element.send_keys("visible=false")
        self.sleep_for(self.wait_types.UX_RENDER)

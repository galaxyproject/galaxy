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
        self.history_panel_build_list_auto()
        self.collection_builder_set_name("my cool list")
        self.screenshot("collection_builder_wizard_list")
        self.collection_builder_create()
        self._wait_for_hid_visible(3)

    @selenium_test
    @managed_history
    def test_build_list_and_show_items(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self._wait_for_and_select([1])
        self.history_panel_build_list_auto()
        # this toggles the checkbox to not hide originals
        self.collection_builder_hide_originals()
        self.collection_builder_set_name("my cool list")
        self.collection_builder_create()
        self._wait_for_hid_visible(3)

    @selenium_test
    @managed_history
    def test_build_paired_list_auto_matched(self):
        self.perform_upload_of_pasted_content(
            {
                "basename_1.fasta": "forward content",
                "basename_2.fasta": "reverse content",
            }
        )
        self._wait_for_and_select([1, 2])
        self.history_panel_build_list_of_pairs()
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
    def test_build_paired_list_manual_matched(self):
        self.perform_upload_of_pasted_content(
            {
                "thisdoesnotmatch.fasta": "forward content",
                "becausethenamesarentalike.fasta": "reverse content",
            }
        )
        self._wait_for_and_select([1, 2])
        self.history_panel_build_list_of_pairs()
        self.collection_builder_pair_rows(0, 1)
        row0 = self.components.collection_builders.list_wizard.row._(index=0)
        row0.unlink_button.wait_for_present()
        row0.link_button.assert_absent()

        self.collection_builder_set_name("my awesome paired list manual match")
        self.screenshot("collection_builder_paired_list_manual_match")
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
    def test_build_paired_unpaired_list(self):
        self.perform_upload_of_pasted_content(
            {
                "commonprefix_1.fasta": "forward content",
                "commonprefix_2.fasta": "reverse content",
                "unmatched.fasta": "unmatched",
            }
        )
        self._wait_for_and_select([1, 2, 3])
        self.history_panel_build_list_of_paired_or_unpaireds()

        self.collection_builder_set_name("mix of paired and unpaired data")
        self.screenshot("collection_builder_paired_or_unpaired_list")
        self.collection_builder_create()
        self._wait_for_hid_visible(7)

    @selenium_test
    @managed_history
    def test_build_list_of_lists(self):
        self.perform_upload_of_pasted_content(
            {
                "foo1.txt": "forward content 1",
                "bar1.txt": "reverse content 1",
                "foo2.txt": "forward content 2",
                "bar2.txt": "forward content 2",
            }
        )
        self._wait_for_and_select([1, 2, 3, 4])
        self.history_panel_build_list_of_lists()
        self.list_wizard_click_cell_and_send_keys("outerIdentifier", 2, "outer1")
        self.list_wizard_click_cell_and_send_keys("outerIdentifier", 3, "outer1")
        self.list_wizard_click_cell_and_send_keys("outerIdentifier", 4, "outer2")
        self.list_wizard_click_cell_and_send_keys("outerIdentifier", 5, "outer2")
        self.collection_builder_set_name("nested list")
        self.screenshot("collection_builder_list_list")
        self.collection_builder_create()
        self._wait_for_hid_visible(9)

    @selenium_test
    @managed_history
    def test_build_paired_list_show_original(self):
        self.perform_upload_of_pasted_content(
            {
                "thisdoesnotmatch.fasta": "forward content",
                "becausethenamesarentalike.fasta": "reverse content",
            }
        )
        self._wait_for_and_select([1, 2])
        self.history_panel_build_list_of_pairs()

        self.collection_builder_pair_rows(0, 1)
        row0 = self.components.collection_builders.list_wizard.row._(index=0)
        row0.unlink_button.wait_for_present()
        row0.link_button.assert_absent()

        self.collection_builder_hide_originals()
        self.collection_builder_set_name("my awesome paired list shown originals")
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
        self.perform_upload_of_pasted_content(
            {
                "1.fasta": "fasta content",
            }
        )
        self._wait_for_and_select([1])
        self.history_panel_build_rule_builder_for_selection()
        self.collection_builder_set_name("my cool list from rules originals hidden")
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

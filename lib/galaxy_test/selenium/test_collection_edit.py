from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestCollectionEdit(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_change_dbkey_simple_list(self):
        self._create_simple_list_collection("1.fasta", "fasta")
        self.open_collection_edit_view()
        self.navigate_to_database_tab()
        alert_element = self.components.edit_collection_attributes.alert_info.wait_for_visible()
        assert "This will create a new collection in your History. Your quota will not increase." in alert_element.text
        dataValue = "unspecified"
        self.check_current_data_value(dataValue)
        dataNew = "hg17"
        self.change_dbkey_value_and_click_submit(dataValue, dataNew)
        self.history_panel_wait_for_hid_ok(5)
        self.open_collection_edit_view()
        self.navigate_to_database_tab()
        self.check_current_data_value(dataNew)

    @selenium_test
    @managed_history
    def test_change_datatype_simple_list(self):
        self._create_simple_list_collection("1.txt", "txt")
        self.open_collection_edit_view()
        self.navigate_to_datatype_tab()
        alert_element = self.components.edit_collection_attributes.alert_info.wait_for_visible()

        assert (
            "This operation might take a short while, depending on the size of your collection." in alert_element.text
        )
        dataValue = "txt"
        self.check_current_data_value(dataValue)
        dataNew = "tabular"
        self.change_datatype_value_and_click_submit(dataValue, dataNew)
        self.check_current_data_value(dataNew)
        self.wait_for_history()
        self.history_panel_expand_collection(3)
        self.history_panel_ensure_showing_item_details(1)
        item = self.history_panel_item_component(hid=1)
        item.datatype.wait_for_visible()
        assert item.datatype.wait_for_text() == dataNew

    def _create_simple_list_collection(self, filename, ext):
        self.perform_upload(self.get_filename(filename), ext=ext)
        self._wait_for_and_select([1])

        self._collection_dropdown("build list")

        self.collection_builder_set_name("my cool list")
        self.collection_builder_create()
        self._wait_for_hid_visible(3)

    def open_collection_edit_view(self):
        self.components.history_panel.collection_menu_edit_attributes.wait_for_and_click()

    def navigate_to_database_tab(self):
        self._edit_attributes.database_genome_tab.wait_for_and_click()

    def navigate_to_datatype_tab(self):
        self._edit_attributes.datatypes_tab.wait_for_and_click()

    def check_current_data_value(self, dataValue):
        self._edit_attributes.data_value(data_change=dataValue).wait_for_visible()

    def change_dbkey_value_and_click_submit(self, dataValue, dataNew):
        self._edit_attributes.data_value(data_change=dataValue).wait_for_and_click()
        self._edit_attributes.genome_select_search.wait_for_and_send_keys(dataNew)
        self._edit_attributes.genome_select_search.wait_for_and_send_keys(self.keys.ENTER)
        self._edit_attributes.save_dbkey_btn.wait_for_and_click()

    def change_datatype_value_and_click_submit(self, dataValue, dataNew):
        self._edit_attributes.data_value(data_change=dataValue).wait_for_and_click()
        self._edit_attributes.datatype_select_search.wait_for_and_send_keys(dataNew)
        self._edit_attributes.datatype_select_search.wait_for_and_send_keys(self.keys.ENTER)
        self._edit_attributes.save_datatype_btn.wait_for_and_click()

    @property
    def _edit_attributes(self):
        return self.components.edit_collection_attributes

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

    def _collection_dropdown(self, option_description):
        return self.use_bootstrap_dropdown(option=option_description, menu="selected content menu")

    def _wait_for_hid_visible(self, hid, state="ok"):
        timeout = self.wait_length(self.wait_types.JOB_COMPLETION)
        row_selector = self.content_item_by_attributes(hid=hid, state=state)
        self.wait_for_visible(row_selector, timeout=timeout)

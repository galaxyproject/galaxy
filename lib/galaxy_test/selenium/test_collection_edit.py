from selenium.webdriver.common.keys import Keys

from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class CollectionEditTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_change_dbkey_simple_list(self):
        self.use_beta_history()
        self.create_simple_list_collection()
        self.open_collection_edit_view()
        self.navigate_to_database_tab()
        dbkeyValue = "unspecified"
        self.check_current_dbkey_value(dbkeyValue)
        dbkeyNew = "hg17"
        self.change_dbkey_value_and_click_submit(dbkeyValue, dbkeyNew)
        self.history_panel_wait_for_hid_ok(4)
        self.use_beta_history()
        self.open_collection_edit_view()
        self.navigate_to_database_tab()
        self.check_current_dbkey_value(dbkeyNew)

    def create_simple_list_collection(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self._wait_for_and_select([1])

        self._collection_dropdown("build list")

        self.collection_builder_set_name("my cool list")
        self.screenshot("collection_builder_list")
        self.collection_builder_create()
        self._wait_for_hid_visible(2)

    def open_collection_edit_view(self):
        self.components.history_panel.collection_menu_edit_attributes.wait_for_and_click()

    def navigate_to_database_tab(self):
        self.components.edit_collection_attributes.database_genome_tab.wait_for_and_click()

    def check_current_dbkey_value(self, dbkeyValue):
        self.components.edit_collection_attributes.database_value(dbkey=dbkeyValue).wait_for_visible()

    def change_dbkey_value_and_click_submit(self, dbkeyValue, dbkeyNew):
        self.components.edit_collection_attributes.database_value(dbkey=dbkeyValue).wait_for_and_click()
        self.driver.find_element_by_css_selector("input.multiselect__input").send_keys(dbkeyNew)
        self.driver.find_element_by_css_selector("input.multiselect__input").send_keys(Keys.ENTER)
        self.components.edit_collection_attributes.save_btn.wait_for_and_click()

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

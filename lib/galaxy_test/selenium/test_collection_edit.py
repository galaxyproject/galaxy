from .framework import (
    selenium_test,
    SeleniumTestCase
)
from selenium.webdriver.common.keys import Keys


class CollectionEditTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_change_dbkey_simple_list(self):
        self.create_simple_list_collection()
        self.switch_to_beta_history()
        self.open_collection_edit_view()
        self.navigate_to_database_tab()
        dbkeyValue="Additional"
        self.check_current_dbkey_value(dbkeyValue)
        dbkeyNew="hg17"
        self.change_dbkey_value_and_click_submit(dbkeyValue,dbkeyNew)
        # self.history_panel.history_panel_wait_for_hid_ok(3)
        self.open_collection_edit_view()
        self.navigate_to_database_tab()
        self.check_current_dbkey_value(dbkeyNew)

    def create_simple_list_collection(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        self.history_panel_multi_operations_show()
        self.history_panel_muli_operation_select_hid(1)
        self.history_panel_multi_operation_action_click(self.navigation.history_panel.multi_operations.labels.build_list)

        self.collection_builder_set_name("my cool list")
        self.screenshot("collection_builder_list")
        self.collection_builder_create()
        self.history_panel_wait_for_hid_ok(2)

    def switch_to_beta_history(self):
        self.click_history_options()
        self.components.history_panel.options_use_beta_history.wait_for_and_click()

    def open_collection_edit_view(self):
        self.components.history_panel.collection_menu_button.wait_for_and_click()
        self.components.history_panel.collection_menu_edit_attributes.wait_for_and_click()
       
    def navigate_to_database_tab(self):
        self.components.edit_collection_attributes.database_genome_tab.wait_for_and_click()

    def check_current_dbkey_value(self,dbkeyValue):
        self.components.edit_collection_attributes.database_value(dbkey=dbkeyValue).wait_for_visible()

    def change_dbkey_value_and_click_submit(self,dbkeyValue,dbkeyNew):
        self.components.edit_collection_attributes.database_value(dbkey=dbkeyValue).wait_for_and_click()
        self.driver.find_element_by_css_selector("input.multiselect__input").send_keys(dbkeyNew)
        self.driver.find_element_by_css_selector("input.multiselect__input").send_keys(Keys.ENTER)
        self.components.edit_collection_attributes.save_btn.wait_for_and_click()
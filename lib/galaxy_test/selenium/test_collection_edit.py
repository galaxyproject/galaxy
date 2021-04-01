from .framework import (
    selenium_test,
    SeleniumTestCase
)


class CollectionEditTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_change_dbkey_simple_list(self):
        self.create_simple_list_collection()
        self.switch_to_beta_history()
        self.open_collection_edit_view()
        self.navigate_to_database_tab()
        self.check_current_value()

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

    def check_current_value(self):
        self.components.edit_collection_attributes.database_value(dbkey="Additional Species Are Below").wait_for_and_click()

        # assert dbkey is hg 17 (?)

        # open edit collection view
        # navigate to dbkey 
        # change dbkey 
        # click submit
        # assert dbkey changed to whatever it was set to
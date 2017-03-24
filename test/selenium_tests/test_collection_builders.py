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

        name_element = self.wait_for_selector_visible("input.collection-name")
        name_element.send_keys("my cool list")

        create_element = self.wait_for_selector_clickable("button.create-collection")
        create_element.click()
        self.history_panel_wait_for_hid_ok(2)

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
        name_element = self.wait_for_selector_visible("input.collection-name")
        name_element.send_keys("my awesome pair")

        create_element = self.wait_for_selector_clickable("button.create-collection")
        create_element.click()
        self.history_panel_wait_for_hid_ok(3)

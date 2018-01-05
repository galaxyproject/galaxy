from .framework import (
    selenium_test,
    SeleniumTestCase
)


class HistoryMultiViewTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_create_new_old_slides_next(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json()
        input_hid = input_collection["hid"]

        self.home()

        hdca_selector = self.history_panel_wait_for_hid_state(input_hid, "ok")

        self.components.history_panel.multi_view_button.wait_for_and_click()
        self.components.multi_history_view.create_new_button.wait_for_and_click()
        self.components.multi_history_view.drag_drop_help.wait_for_visible()
        self.wait_for_visible(hdca_selector)
        self.screenshot("multi_history_collection")

    @selenium_test
    def test_list_list_display(self):
        history_id = self.current_history_id()
        collection = self.dataset_collection_populator.create_list_of_list_in_history(history_id).json()
        collection_hid = collection["hid"]

        self.home()

        self.components.history_panel.multi_view_button.wait_for_and_click()

        selector = self.history_panel_wait_for_hid_state(collection_hid, "ok")
        self.click(selector)
        first_level_element_selector = selector.descendant(".dataset-collection-element")
        self.wait_for_and_click(first_level_element_selector)
        dataset_selector = first_level_element_selector.descendant(".dataset")
        self.wait_for_and_click(dataset_selector)

        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("multi_history_list_list")

    @selenium_test
    def test_list_list_list_display(self):
        history_id = self.current_history_id()
        collection = self.dataset_collection_populator.create_nested_collection(history_id, collection_type="list:list:list").json()
        collection_hid = collection["hid"]

        self.home()

        self.components.history_panel.multi_view_button.wait_for_and_click()

        selector = self.history_panel_wait_for_hid_state(collection_hid, "ok")
        self.click(selector)
        first_level_element_selector = selector.descendant(".dataset-collection-element")
        self.wait_for_and_click(first_level_element_selector)
        second_level_element_selector = first_level_element_selector.descendant(".dataset-collection-element")
        self.wait_for_and_click(second_level_element_selector)
        dataset_selector = first_level_element_selector.descendant(".dataset")
        self.wait_for_and_click(dataset_selector)

        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("multi_history_list_list_list")

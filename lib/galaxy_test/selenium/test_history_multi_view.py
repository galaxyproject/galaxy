from selenium.common.exceptions import NoSuchElementException

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
        method = self.dataset_collection_populator.create_list_of_list_in_history(history_id).json
        selector = self.prepare_multi_history_view(method)
        first_level_element_selector = selector.descendant(".dataset-collection-element")
        self.wait_for_and_click(first_level_element_selector)
        dataset_selector = first_level_element_selector.descendant(".dataset")
        self.wait_for_and_click(dataset_selector)

        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("multi_history_list_list")

    @selenium_test
    def test_list_list_list_display(self):
        history_id = self.current_history_id()
        method = self.dataset_collection_populator.create_nested_collection(history_id, collection_type="list:list:list").json
        selector = self.prepare_multi_history_view(method)

        first_level_element_selector = selector.descendant(".dataset-collection-element")
        self.wait_for_and_click(first_level_element_selector)
        second_level_element_selector = first_level_element_selector.descendant(".dataset-collection-element")
        self.wait_for_and_click(second_level_element_selector)
        dataset_selector = first_level_element_selector.descendant(".dataset")
        self.wait_for_and_click(dataset_selector)

        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("multi_history_list_list_list")

    @selenium_test
    def test_copy_history(self):
        history_id = self.current_history_id()
        method = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json

        self.prepare_multi_history_view(method)
        self.copy_history(history_id)
        self.assert_history(history_id, histories_number=2)

    @selenium_test
    def test_delete_history(self):
        history_id = self.current_history_id()
        method = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json

        self.prepare_multi_history_view(method)
        self.copy_history(history_id)
        self.components.multi_history_view.history_dropdown_btn(history_id=history_id).wait_for_and_click()
        # click on delete button with corresponding history_id
        self.components.multi_history_view.history_dropdown_menu.delete(history_id=history_id).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_history(history_id, should_exist=False)

    @selenium_test
    def test_purge_history(self):
        history_id = self.current_history_id()
        method = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json

        self.prepare_multi_history_view(method)
        self.copy_history(history_id)
        self.components.multi_history_view.history_dropdown_btn(history_id=history_id).wait_for_and_click()
        # click on purge button with corresponding history_id
        self.components.multi_history_view.history_dropdown_menu.purge(history_id=history_id).wait_for_and_click()

        self.driver.switch_to_alert().accept()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_history(history_id, should_exist=False)

    @selenium_test
    def test_switching_history(self):
        history_id = self.current_history_id()
        method = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json

        self.prepare_multi_history_view(method)
        self.copy_history(history_id)
        self.components.multi_history_view.switch_history.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_history(history_id, histories_number=2)
        # assert that id of current history equals history_id
        assert self.components.multi_history_view.current_history_check(history_id=history_id).is_displayed
        self.components.multi_history_view.switch_history.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        # assert that 'history_id' is not current history
        self.assertRaises(NoSuchElementException, lambda:
                          self.components.multi_history_view.current_history_check(history_id=history_id).is_displayed)

    @selenium_test
    def test_create_new_history(self):
        history_id = self.current_history_id()
        method = self.dataset_collection_populator.create_list_in_history(history_id, contents=["0", "1", "0", "1"]).json

        self.prepare_multi_history_view(method)
        # assert that empty history is not created in advance
        self.components.multi_history_view.empty_message_check.assert_absent_or_hidden()

        self.components.multi_history_view.create_new_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_history(history_id, histories_number=2)
        self.sleep_for(self.wait_types.UX_RENDER)

        # assert that empty history is present
        self.components.multi_history_view.empty_message_check.wait_for_present()

    def assert_history(self, history_id, histories_number=1, should_exist=True):
        histories = self.components.multi_history_view.histories.all()
        assert len(histories) == histories_number
        # search for history with history_id
        assert should_exist == any(history.get_attribute("id") == "history-column-" + history_id for history in histories)

    def copy_history(self, history_id):
        self.components.multi_history_view.history_dropdown_btn(history_id=history_id).wait_for_and_click()
        self.components.multi_history_view.copy.wait_for_and_click()
        self.components.multi_history_view.copy_history_modal.copy_btn.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    def prepare_multi_history_view(self, collection_populator_method):
        collection = collection_populator_method()
        collection_hid = collection["hid"]

        self.home()
        self.components.history_panel.multi_view_button.wait_for_and_click()

        selector = self.history_panel_wait_for_hid_state(collection_hid, "ok")
        self.click(selector)
        return selector

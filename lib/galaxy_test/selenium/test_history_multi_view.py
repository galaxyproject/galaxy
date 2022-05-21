from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class HistoryMultiViewTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_create_new_old_slides_next(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1", "0", "1"], wait=True
        ).json()
        input_hid = input_collection["outputs"][0]["hid"]

        self.home()

        self.open_history_multi_view()
        hdca_selector = self.history_panel_wait_for_hid_state(input_hid, "ok", multi_history_panel=True)
        self.wait_for_visible(hdca_selector)
        self.components.multi_history_view.create_new_button.wait_for_and_click()
        self.components.multi_history_view.drag_drop_help.wait_for_visible()
        self.screenshot("multi_history_collection")

    @selenium_test
    def test_list_list_display(self):
        history_id = self.current_history_id()
        method = self.dataset_collection_populator.create_list_of_list_in_history(history_id, wait=True).json
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
        method = self.dataset_collection_populator.create_nested_collection(
            history_id, collection_type="list:list:list"
        ).json
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
        method = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1", "0", "1"]
        ).json

        self.prepare_multi_history_view(method)
        self.copy_history(history_id)
        self.assert_history(history_id, histories_number=2)

    @selenium_test
    def test_delete_history(self):
        history_id = self.current_history_id()
        method = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1", "0", "1"]
        ).json

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
        method = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1", "0", "1"]
        ).json

        self.prepare_multi_history_view(method)
        self.copy_history(history_id)
        self.components.multi_history_view.history_dropdown_btn(history_id=history_id).wait_for_and_click()
        # click on purge button with corresponding history_id
        self.components.multi_history_view.history_dropdown_menu.purge(history_id=history_id).wait_for_and_click()

        self.driver.switch_to.alert.accept()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.assert_history(history_id, should_exist=False)

    @selenium_test
    def test_switch_history(self):
        """
        1. Load the multi history view. There should be a selector for the button
           to create a new history.
        2. Create a new history. This *should* automatically switch to the newly
           created history.
        3. Switch back to the original history. A button should appear on the old,
           previously created history that allows switching back to that one, and
           the history ID should now match the ID of the history with which we
           started.
        """
        self.home()
        original_history_id = self.current_history_id()
        # Load the multi-view
        self.open_history_multi_view()
        # There should be only one
        self.assert_history(original_history_id, histories_number=1)
        # Creating a new history should automatically switch to it
        self.components.multi_history_view.create_new_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        new_history_id = self.current_history_id()
        # Otherwise this assertion would fail
        self.screenshot("multi_history_switch_created_history")
        self.assertNotEqual(original_history_id, new_history_id)
        # Switch back to the original history
        switch_button = self.components.multi_history_view.switch_button(history_id=original_history_id)
        switch_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("multi_history_switch_changed_history")
        self.assertEqual(original_history_id, self.current_history_id())

    def assert_history(self, history_id, histories_number=1, should_exist=True):
        self.components.multi_history_view.histories.wait_for_present()
        histories = self.components.multi_history_view.histories.all()
        assert len(histories) == histories_number
        # search for history with history_id
        assert should_exist == any(
            history.get_attribute("id") == f"history-column-{history_id}" for history in histories
        )

    def copy_history(self, history_id):
        self.components.multi_history_view.history_dropdown_btn(history_id=history_id).wait_for_and_click()
        self.components.multi_history_view.copy.wait_for_and_click()
        self.components.multi_history_view.copy_history_modal.copy_btn.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    def prepare_multi_history_view(self, collection_populator_method):
        collection = collection_populator_method()
        if "outputs" in collection:
            collection = self.dataset_collection_populator.wait_for_fetched_collection(collection)
        collection_hid = collection["hid"]

        self.home()
        self.open_history_multi_view()

        selector = self.history_panel_wait_for_hid_state(collection_hid, "ok", multi_history_panel=True)
        self.click(selector)
        return selector

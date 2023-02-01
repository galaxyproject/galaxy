from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestHistoryCopyElements(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_copy_hdca(self):
        history_id = self.current_history_id()
        input_collection = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["0", "1", "0", "1"], wait=True
        ).json()["outputs"][0]
        input_hid = input_collection["hid"]

        failed_response = self.dataset_populator.run_exit_code_from_file(history_id, input_collection["id"])
        failed_collection = failed_response["implicit_collections"][0]
        failed_hid = failed_collection["hid"]

        self.history_panel_wait_for_hid_state(input_hid, "ok")
        self.history_panel_wait_for_hid_state(failed_hid, "error")
        self.history_panel_click_copy_elements()

        with self.main_panel():
            self.components.history_copy_elements.collection_checkbox(id=input_collection["id"]).wait_for_and_click()
            self.components.history_copy_elements.collection_checkbox(id=failed_collection["id"]).wait_for_and_click()

            text_element = self.components.history_copy_elements.new_history_name.wait_for_and_click()
            text_element.send_keys("newhistfor_copy_hdca")
            self.components.history_copy_elements.copy_button.wait_for_and_click()
            self.sleep_for(self.wait_types.UX_TRANSITION)
            self.components.history_copy_elements.done_link.wait_for_and_click()

        # I don't know why this sleep is necessary but it seems to be
        self.sleep_for(self.wait_types.UX_RENDER)
        # Okay copied first
        self.history_panel_wait_for_hid_state(5, "ok")
        # Then 4 datasets and then the failed collection (this was six when coming from the original history)
        self.history_panel_wait_for_hid_state(10, "error")

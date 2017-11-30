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

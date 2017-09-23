import time

from .framework import (
    selenium_test,
    SeleniumTestCase
)


class HistoryPanelTestCase(SeleniumTestCase):

    @selenium_test
    def test_history_panel_landing_state(self):
        self.register()
        self.assert_initial_history_panel_state_correct()

        tag_icon_selector = self.test_data["historyPanel"]["selectors"]["history"]["tagIcon"]
        anno_icon_selector = self.test_data["historyPanel"]["selectors"]["history"]["annoIcon"]
        self.assert_selector(tag_icon_selector)
        self.assert_selector(anno_icon_selector)

        name_element = self.history_panel_name_element()
        self.assert_tooltip_text(name_element, self.test_data["historyPanel"]["text"]["history"]["tooltips"]["name"])

    @selenium_test
    def test_history_panel_rename(self):
        self.register()
        editable_text_input_element = self.history_panel_click_to_rename()
        editable_text_input_element.send_keys("New History Name")
        self.send_enter(editable_text_input_element)

        assert "New History Name" in self.history_panel_name()

    @selenium_test
    def test_history_rename_cancel_with_click(self):
        self.register()
        editable_text_input_element = self.history_panel_click_to_rename()
        editable_text_input_element.send_keys("New History Name")
        self.click_center()
        self.assert_selector_absent(self.history_panel_edit_title_input_selector())
        assert "New History Name" not in self.history_panel_name()

    @selenium_test
    def test_history_rename_cancel_with_escape(self):
        self.register()
        editable_text_input_element = self.history_panel_click_to_rename()
        editable_text_input_element.send_keys("New History Name")
        self.send_escape(editable_text_input_element)
        self.assert_selector_absent(self.history_panel_edit_title_input_selector())
        assert "New History Name" not in self.history_panel_name()

    @selenium_test
    def test_history_tags_and_annotations_buttons(self):
        # TODO: Test actually editing these values.
        self.register()

        tag_icon_selector = self.test_data["historyPanel"]["selectors"]["history"]["tagIcon"]
        anno_icon_selector = self.test_data["historyPanel"]["selectors"]["history"]["annoIcon"]
        tag_area_selector = self.test_data["historyPanel"]["selectors"]["history"]["tagArea"]
        anno_area_selector = self.test_data["historyPanel"]["selectors"]["history"]["annoArea"]

        tag_icon = self.wait_for_selector_clickable(tag_icon_selector)
        annon_icon = self.wait_for_selector_clickable(anno_icon_selector)

        self.assert_selector_absent_or_hidden(tag_area_selector)
        self.assert_selector_absent_or_hidden(anno_area_selector)

        tag_icon.click()

        self.wait_for_selector(tag_area_selector)
        self.assert_selector_absent_or_hidden(anno_area_selector)

        tag_icon.click()
        time.sleep(.5)
        annon_icon.click()

        self.wait_for_selector(anno_area_selector)
        self.assert_selector_absent_or_hidden(tag_area_selector)

        annon_icon.click()
        time.sleep(.5)

        self.assert_selector_absent_or_hidden(tag_area_selector)
        self.assert_selector_absent_or_hidden(anno_area_selector)

    @selenium_test
    def test_refresh_preserves_state(self):
        refresh_wait = .5
        self.register()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()

        # Open the details, verify they are open and do a refresh.
        self.history_panel_ensure_showing_item_details(hid=1)
        self.history_panel_item_body_selector(1, wait=True)
        self.history_panel_refresh_click()

        # After the refresh, verify the details are still open.
        time.sleep(refresh_wait)
        self.wait_for_selector_clickable(self.history_panel_item_selector(hid=1))
        assert self.history_panel_item_showing_details(hid=1)

        # Close the detailed display, refresh, and ensure they are still closed.
        self.history_panel_click_item_title(hid=1, wait=True)
        assert not self.history_panel_item_showing_details(hid=1)
        self.history_panel_refresh_click()
        time.sleep(refresh_wait)
        self.wait_for_selector_clickable(self.history_panel_item_selector(hid=1))
        assert not self.history_panel_item_showing_details(hid=1)

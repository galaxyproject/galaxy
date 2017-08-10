import time

from .framework import SeleniumTestCase
from .framework import selenium_test


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
        editable_text_input_element = self.click_to_rename_history()
        editable_text_input_element.send_keys("New History Name")
        self.send_enter(editable_text_input_element)

        name_element = self.history_panel_name_element()
        assert "New History Name" in name_element.text

    @selenium_test
    def test_history_rename_cancel_with_click(self):
        self.register()
        editable_text_input_element = self.click_to_rename_history()
        editable_text_input_element.send_keys("New History Name")
        self.click_center()
        self.assert_selector_absent(self.edit_title_input_selector())
        name_element = self.history_panel_name_element()
        assert "New History Name" not in name_element.text

    @selenium_test
    def test_history_rename_cancel_with_escape(self):
        self.register()
        editable_text_input_element = self.click_to_rename_history()
        editable_text_input_element.send_keys("New History Name")
        self.send_escape(editable_text_input_element)
        self.assert_selector_absent(self.edit_title_input_selector())
        name_element = self.history_panel_name_element()
        assert "New History Name" not in name_element.text

    @selenium_test
    def test_history_tags_and_annotations_buttons(self):
        # TODO: Test actually editing these values.
        self.register()

        tag_icon_selector = self.test_data["historyPanel"]["selectors"]["history"]["tagIcon"]
        anno_icon_selector = self.test_data["historyPanel"]["selectors"]["history"]["annoIcon"]
        tag_area_selector = self.test_data["historyPanel"]["selectors"]["history"]["tagArea"]
        anno_area_selector = self.test_data["historyPanel"]["selectors"]["history"]["annoArea"]

        tag_icon = self.wait_for_selector(tag_icon_selector)
        annon_icon = self.wait_for_selector(anno_icon_selector)

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

    def test_refresh_preserves_state(self):
        self.register()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()

        hda_id = self.latest_history_item()["id"]
        hda_body_selector = self.hda_body_selector(hda_id)
        self.assert_selector_absent_or_hidden(hda_body_selector)

        self.click_hda_title(hda_id, wait=True)
        self.wait_for_selector_visible(hda_body_selector)

        self.click_history_refresh()

        title_selector = self.hda_div_selector(hda_id)
        self.wait_for_selector_visible(hda_body_selector)

        self.click_hda_title(hda_id, wait=True)
        self.click_history_refresh()

        self.wait_for_selector(title_selector)
        self.assert_selector_absent_or_hidden(hda_body_selector)

    def click_history_refresh(self):
        refresh_button_element = self.wait_for_selector('a#history-refresh-button')
        refresh_button_element.click()

    def click_to_rename_history(self):
        self.history_panel_name_element().click()
        return self.wait_for_selector(self.edit_title_input_selector())

    def edit_title_input_selector(self):
        return self.test_data["historyPanel"]["selectors"]["history"]["nameEditableTextInput"]

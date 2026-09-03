from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity


class TestHistoryOptions(SeleniumTestCase, UsesUploadActivity):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_options(self):
        self.upload_context("paste-content").stage_paste_content("text content").start()
        menu_selector = self.navigation.history_panel.selectors.options_menu
        self.wait_for_absent_or_hidden(menu_selector)
        self.click_history_options()
        component = self.wait_for_visible(menu_selector)
        self.screenshot("history_options")
        self.send_escape(component)
        self.wait_for_absent_or_hidden(menu_selector)
        hid = 1
        self.history_panel_wait_for_hid_state(hid, "ok")
        self.history_panel_click_item_title(hid=hid, wait=True)
        item_component = self.history_panel_item_body_component(hid=hid)
        item_component.wait_for_visible()
        self.history_panel_click_item_title(hid=hid, wait=True)
        item_component.assert_absent_or_hidden_after_transitions()

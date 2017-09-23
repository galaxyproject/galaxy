from .framework import (
    selenium_test,
    SeleniumTestCase
)


class HistoryOptionsTestCase(SeleniumTestCase):

    @selenium_test
    def test_options(self):
        self.register()
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.click_history_options()

        menu_selector = self.history_options_menu_selector()
        self.wait_for_selector_visible(menu_selector)

        # Click away closes history options
        self.click_center()

        self.assert_selector_absent_or_hidden(menu_selector)

        hda = self.latest_history_item()
        hid = hda["hid"]
        self.history_panel_click_item_title(hid=hid, wait=True)

        hda_body_selector = self.hda_body_selector(hda["id"])
        self.wait_for_selector_visible(hda_body_selector)

        self.history_panel_click_item_title(hid=hid, wait=True)

        self.assert_selector_absent_or_hidden_after_transitions(hda_body_selector)

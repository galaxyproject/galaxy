import time

from .framework import SeleniumTestCase
from .framework import selenium_test


class HistoryDatasetStateTestCase(SeleniumTestCase):

    @selenium_test
    def test_dataset_state(self):
        self.register()
        self.perform_upload(self.get_filename("1.fasta"))
        self.wait_for_history()
        hda_id = self.latest_history_item()["id"]
        item_selector = self.hda_div_selector(hda_id)
        self.assert_item_name(item_selector, "1.fasta")
        self.assert_item_hid(item_selector, "1")
        self.assert_title_buttons(item_selector)

        self.click_hda_title(hda_id, wait=True)
        hda_body_selector = self.hda_body_selector(hda_id)
        self.wait_for_selector_visible(hda_body_selector)

        self.assert_item_summary_includes(hda_body_selector, "1 sequence")
        self.assert_dbkey_display_as(hda_body_selector, "?")
        self.assert_info_includes(hda_body_selector, 'uploaded fasta file')
        self.assert_action_buttons(hda_body_selector)
        self.assert_peek_includes(hda_body_selector, ">hg17")

    def assert_action_buttons(self, body_selector, expected_buttons=["info", "download"]):
        buttons_selector = body_selector + " " + self.test_data["historyPanel"]["selectors"]["hda"]["primaryActionButtons"]
        self.wait_for_selector_visible(buttons_selector)

        for expected_button in expected_buttons:
            self._assert_item_button(buttons_selector, expected_button, self.test_data["historyPanel"]["hdaPrimaryActionButtons"][expected_button])

    def assert_peek_includes(self, body_selector, expected):
        peek_selector = body_selector + ' ' + self.test_data["historyPanel"]["selectors"]["hda"]["peek"]
        peek_selector = self.wait_for_selector_visible(peek_selector)

    def assert_info_includes(self, body_selector, expected):
        info_selector = body_selector + ' ' + self.test_data["historyPanel"]["selectors"]["hda"]["info"]
        info_element = self.wait_for_selector_visible(info_selector)
        text = info_element.text
        assert expected in text, "Failed to find expected info text [%s] in info [%s]" % (expected, text)

    def assert_dbkey_display_as(self, body_selector, dbkey):
        dbkey_selector = body_selector + ' ' + self.test_data["historyPanel"]["selectors"]["hda"]["dbkey"]
        dbkey_element = self.wait_for_selector_visible(dbkey_selector)
        assert dbkey in dbkey_element.text

    def assert_item_summary_includes(self, body_selector, expected_text):
        summary_selector = "%s %s" % (body_selector, self.test_data["historyPanel"]["selectors"]["hda"]["summary"])
        summary_element = self.wait_for_selector_visible(summary_selector)
        text = summary_element.text
        assert expected_text in text, "Expected summary [%s] not found in [%s]." % (expected_text, text)

    def assert_item_name(self, item_selector, name):
        title_selector = item_selector + ' ' + self.test_data["historyPanel"]["selectors"]["hda"]["name"]
        title_element = self.wait_for_selector_visible(title_selector)
        assert title_element.text == name, title_element.text

    def assert_item_hid(self, item_selector, hid):
        hid_selector = item_selector + ' ' + self.test_data["historyPanel"]["selectors"]["hda"]["hid"]
        hid_element = self.wait_for_selector_visible(hid_selector)
        assert hid_element.text == hid, hid_element.text

    def assert_title_buttons(self, item_selector, expected_buttons=['display', 'edit', 'delete']):
        buttons_area = item_selector + ' ' + self.test_data["historyPanel"]["selectors"]["hda"]["titleButtonArea"]
        buttons = self.test_data["historyPanel"]["hdaTitleButtons"]

        for expected_button in expected_buttons:
            button = buttons[expected_button]
            self._assert_item_button(buttons_area, expected_button, button)

    def _assert_item_button(self, buttons_area, expected_button, button_def):
        selector = button_def["selector"]
        # Let old tooltip expire, etc...
        time.sleep(1)
        button_item = self.wait_for_selector_visible("%s %s" % (buttons_area, selector))
        expected_tooltip = button_def.get("tooltip")
        self.assert_tooltip_text(button_item, expected_tooltip)

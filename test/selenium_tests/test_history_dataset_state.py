from .framework import (
    SeleniumTestCase,
    selenium_test,
    UsesHistoryItemAssertions,
)


class HistoryDatasetStateTestCase(SeleniumTestCase, UsesHistoryItemAssertions):

    @selenium_test
    def test_dataset_state(self):
        self.register()
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)
        self.assert_item_name(1, "1.fasta")
        self.assert_item_hid_text(1)
        self._assert_title_buttons(1)

        # Expand HDA
        self.history_panel_click_item_title(hid=1, wait=True)

        self.assert_item_summary_includes(1, "1 sequence")
        self.assert_item_dbkey_displayed_as(1, "?")
        self.assert_item_info_includes(1, 'uploaded fasta file')
        self.assert_item_peek_includes(1, ">hg17")

        self._assert_action_buttons(1)

    def _assert_title_buttons(self, hid, expected_buttons=['display', 'edit', 'delete']):
        item_selector = self.history_panel_item_selector(hid, wait=True)
        buttons_area = item_selector + ' ' + self.test_data["historyPanel"]["selectors"]["hda"]["titleButtonArea"]
        buttons = self.test_data["historyPanel"]["hdaTitleButtons"]

        for expected_button in expected_buttons:
            button = buttons[expected_button]
            self._assert_item_button(buttons_area, expected_button, button)

    def _assert_action_buttons(self, hid, expected_buttons=["info", "download"]):
        item_body_selector = self.history_panel_item_body_selector(hid=hid)
        self.wait_for_selector_visible(item_body_selector)

        buttons_selector = item_body_selector + " " + self.test_data["historyPanel"]["selectors"]["hda"]["primaryActionButtons"]
        self.wait_for_selector_visible(buttons_selector)

        for expected_button in expected_buttons:
            self._assert_item_button(buttons_selector, expected_button, self.test_data["historyPanel"]["hdaPrimaryActionButtons"][expected_button])

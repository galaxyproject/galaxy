from .framework import (
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)

BUTTON_TOOLTIPS = {
    "display": 'View data',
    "edit": 'Edit attributes',
    "delete": 'Delete',
    "download": 'Download',
    "info": 'View details',
    "rerun": 'Run this job again',
}


class HistoryDatasetStateTestCase(SeleniumTestCase, UsesHistoryItemAssertions):

    @selenium_test
    def test_dataset_state(self):
        self.register()
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)
        self.assert_item_name(1, "1.fasta")
        self.assert_item_hid_text(1)
        self._assert_title_buttons(1)

        # Expand HDA and wait for details to show up.
        self.history_panel_click_item_title(hid=1, wait=True)
        self.history_panel_item_body_component(1, wait=True)

        self.assert_item_summary_includes(1, "1 sequence")
        self.assert_item_dbkey_displayed_as(1, "?")
        self.assert_item_info_includes(1, 'uploaded fasta file')
        self.assert_item_peek_includes(1, ">hg17")

        self.screenshot("history_panel_dataset_expanded")

        self._assert_action_buttons(1)

    def _assert_title_buttons(self, hid, expected_buttons=['display', 'edit', 'delete']):
        self._assert_buttons(hid, expected_buttons)

    def _assert_action_buttons(self, hid, expected_buttons=["info", "download"]):
        self._assert_buttons(hid, expected_buttons)

    def _assert_buttons(self, hid, expected_buttons):
        item_button = self.history_panel_item_component(hid=hid)
        # Let old tooltip expire, etc...
        for expected_button in expected_buttons:
            self.sleep_for(self.wait_types.UX_TRANSITION)
            button = item_button["%s_button" % expected_button]
            self.assert_tooltip_text(button.wait_for_visible(), BUTTON_TOOLTIPS[expected_button])

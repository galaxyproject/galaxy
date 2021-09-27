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
EXPECTED_TOOLHELP_TITLE_TEXT = 'Tool help for Upload File'
TEST_DBKEY_TEXT = 'Honeybee (Apis mellifera): apiMel3 (apiMel3)'
FIRST_HID = 1


class HistoryDatasetStateTestCase(SeleniumTestCase, UsesHistoryItemAssertions):
    ensure_registered = True

    @selenium_test
    def test_dataset_state(self):
        item = self._prepare_dataset()
        self.history_panel_item_body_component(FIRST_HID, wait=True)

        self.assert_item_summary_includes(FIRST_HID, "1 sequence")
        self.assert_item_dbkey_displayed_as(FIRST_HID, "?")
        self.assert_item_info_includes(FIRST_HID, 'uploaded fasta file')
        self.assert_item_peek_includes(FIRST_HID, ">hg17")

        item.dbkey_button.wait_for_and_click()
        toolhelp_title_text = item.toolhelp_title.wait_for_visible().text
        # assert tool helptext
        assert EXPECTED_TOOLHELP_TITLE_TEXT == toolhelp_title_text, "Toolhelp title [{}] was not expected text [{}].".format(
            EXPECTED_TOOLHELP_TITLE_TEXT, toolhelp_title_text)

        self.screenshot("history_panel_dataset_expanded")

        self._assert_action_buttons(FIRST_HID)

    @selenium_test
    def test_dataset_change_dbkey(self):
        item = self._prepare_dataset()
        self.assert_item_dbkey_displayed_as(FIRST_HID, "?")
        item.dbkey.wait_for_and_click()
        self.components.edit_dataset_attributes.database_build_dropdown.wait_for_and_click()
        # choose database option from 'Database/Build' dropdown, that equals to dbkey_text
        self.components.edit_dataset_attributes.dbkey_dropdown_results.dbkey_dropdown_option(
            dbkey_text=TEST_DBKEY_TEXT).wait_for_and_click()
        self.components.edit_dataset_attributes.save_btn.wait_for_and_click()
        self.history_panel_wait_for_hid_ok(FIRST_HID)
        self.assert_item_dbkey_displayed_as(FIRST_HID, "apiMel3")

    def _prepare_dataset(self):
        self.history_panel_create_new()
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(FIRST_HID)
        self.assert_item_name(FIRST_HID, "1.fasta")
        self.assert_item_hid_text(FIRST_HID)
        self._assert_title_buttons(FIRST_HID)

        # Expand HDA and wait for details to show up.
        return self.history_panel_click_item_title(hid=FIRST_HID, wait=True)

    def _assert_title_buttons(self, hid, expected_buttons=None):
        if expected_buttons is None:
            expected_buttons = ['display', 'edit', 'delete']
        self._assert_buttons(hid, expected_buttons)

    def _assert_action_buttons(self, hid, expected_buttons=None):
        if expected_buttons is None:
            expected_buttons = ["info", "download"]
        self._assert_buttons(hid, expected_buttons)

    def _assert_buttons(self, hid, expected_buttons):
        item_button = self.history_panel_item_component(hid=hid)
        for i, expected_button in enumerate(expected_buttons):

            # ensure old tooltip expired,
            # no tooltip appeared before the 1st element
            if i > 0:
                previous_button = item_button[f"{expected_buttons[i - 1]}_button"].wait_for_visible()
                if previous_button.get_attribute("aria-describedby") is not None:
                    # wait for tooltip to disappear
                    self.components._.tooltip_balloon.wait_for_absent()

            button = item_button[f"{expected_button}_button"]
            self.assert_tooltip_text(button.wait_for_visible(), BUTTON_TOOLTIPS[expected_button])

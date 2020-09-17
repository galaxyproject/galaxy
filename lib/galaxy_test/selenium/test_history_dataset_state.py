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


class HistoryDatasetStateTestCase(SeleniumTestCase, UsesHistoryItemAssertions):
    hid = 1

    @selenium_test
    def test_dataset_state(self, hid=hid):
        item = self._prepare_dataset(self.hid)
        self.history_panel_item_body_component(hid, wait=True)

        self.assert_item_summary_includes(hid, "1 sequence")
        self.assert_item_dbkey_displayed_as(hid, "?")
        self.assert_item_info_includes(hid, 'uploaded fasta file')
        self.assert_item_peek_includes(hid, ">hg17")

        item.dbkey_button.wait_for_and_click()
        toolhelp_title_text = item.toolhelp_title.wait_for_visible().text
        # assert tool helptext
        assert EXPECTED_TOOLHELP_TITLE_TEXT == toolhelp_title_text, "Toolhelp title [%s] was not expected text [%s]." % (
            EXPECTED_TOOLHELP_TITLE_TEXT, toolhelp_title_text)

        self.screenshot("history_panel_dataset_expanded")

        self._assert_action_buttons(hid)

    @selenium_test
    def test_dataset_change_dbkey(self, hid=hid):
        item = self._prepare_dataset(hid)
        self.assert_item_dbkey_displayed_as(hid, "?")
        item.dbkey.wait_for_and_click()
        self.components.edit_dataset_attributes.database_build_dropdown.wait_for_and_click()
        # choose database option from 'Database/Build' dropdown, that equals to dbkey_text
        self.components.edit_dataset_attributes.dbkey_dropdown_results.dbkey_dropdown_option(
            dbkey_text=TEST_DBKEY_TEXT).wait_for_and_click()
        self.components.edit_dataset_attributes.save_btn.wait_for_and_click()
        self.history_panel_wait_for_hid_ok(hid)
        self.assert_item_dbkey_displayed_as(hid, "apiMel3")

    def _prepare_dataset(self, hid):
        self.register()
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(hid)
        self.assert_item_name(hid, "1.fasta")
        self.assert_item_hid_text(hid)
        self._assert_title_buttons(hid)

        # Expand HDA and wait for details to show up.
        return self.history_panel_click_item_title(hid=hid, wait=True)

    def _assert_title_buttons(self, hid, expected_buttons=['display', 'edit', 'delete']):
        self._assert_buttons(hid, expected_buttons)

    def _assert_action_buttons(self, hid, expected_buttons=["info", "download"]):
        self._assert_buttons(hid, expected_buttons)

    def _assert_buttons(self, hid, expected_buttons):
        item_button = self.history_panel_item_component(hid=hid)
        for i, expected_button in enumerate(expected_buttons):

            # ensure old tooltip expired,
            # no tooltip appeared before the 1st element
            if i > 0:
                previous_button = item_button["%s_button" % expected_buttons[i - 1]].wait_for_visible()
                if previous_button.get_attribute("aria-describedby") is not None:
                    # wait for tooltip to disappear
                    self.components._.tooltip_balloon.wait_for_absent()

            button = item_button["%s_button" % expected_button]
            self.assert_tooltip_text(button.wait_for_visible(), BUTTON_TOOLTIPS[expected_button])

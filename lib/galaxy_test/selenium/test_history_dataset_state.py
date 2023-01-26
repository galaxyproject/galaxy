from galaxy.model.unittest_utils.store_fixtures import (
    deferred_hda_model_store_dict,
    one_hda_model_store_dict,
    TEST_SOURCE_URI,
)
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)

BUTTON_TOOLTIPS = {
    "display": "View data",
    "edit": "Edit attributes",
    "delete": "Delete",
    "download": "Download",
    "info": "View details",
    "rerun": "Run this job again",
}
EXPECTED_TOOLHELP_TITLE_TEXT = "Tool help for Data Fetch"
TEST_DBKEY_TEXT = "Honeybee (Apis mellifera): apiMel3 (apiMel3)"
FIRST_HID = 1


class TestHistoryDatasetState(SeleniumTestCase, UsesHistoryItemAssertions):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_dataset_state(self):
        self._prepare_dataset()
        self.history_panel_item_body_component(FIRST_HID, wait=True)
        self.assert_item_summary_includes(FIRST_HID, "1 sequence")
        self.assert_item_dbkey_displayed_as(FIRST_HID, "?")
        self.assert_item_info_includes(FIRST_HID, "uploaded fasta file")
        self.assert_item_peek_includes(FIRST_HID, ">hg17")
        self.screenshot("history_panel_dataset_before_click_dbkey")
        self._assert_action_buttons(FIRST_HID)
        self._assert_downloadable(FIRST_HID)
        self.history_panel_item_view_dataset_details(FIRST_HID)
        self.screenshot("dataset_details_ok")

    @selenium_test
    @managed_history
    def test_dataset_change_dbkey(self):
        item = self._prepare_dataset()
        self.assert_item_dbkey_displayed_as(FIRST_HID, "?")
        item.dbkey.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("history_panel_edit_dbkey_post_click")
        self.components.edit_dataset_attributes.database_build_dropdown.wait_for_and_click()
        # choose database option from 'Database/Build' dropdown, that equals to dbkey_text
        self.components.edit_dataset_attributes.dbkey_dropdown_results.dbkey_dropdown_option(
            dbkey_text=TEST_DBKEY_TEXT
        ).wait_for_and_click()
        self.components.edit_dataset_attributes.save_btn.wait_for_and_click()
        self.sleep_for(self.wait_types.JOB_COMPLETION)
        self.history_panel_wait_for_hid_ok(FIRST_HID)
        self.assert_item_dbkey_displayed_as(FIRST_HID, "apiMel3")

    @selenium_test
    @managed_history
    def test_dataset_state_discarded(self):
        self.history_panel_create_new()
        history_id = self.current_history_id()
        self.dataset_populator.create_contents_from_store(
            history_id,
            store_dict=one_hda_model_store_dict(include_source=False),
        )
        # regression after 3/24/2022 - explicit refresh now required.
        self.home()
        self.history_panel_wait_for_hid_state(FIRST_HID, state="discarded", allowed_force_refreshes=1)
        self.history_panel_click_item_title(hid=FIRST_HID, wait=True)
        self.screenshot("history_panel_dataset_discarded")
        # Next if is a hack for recent changes to beta history...
        # https://github.com/galaxyproject/galaxy/pull/13477/files#r823842897
        self._assert_downloadable(FIRST_HID, is_downloadable=False)

        self.history_panel_item_view_dataset_details(FIRST_HID)
        self.screenshot("dataset_details_discarded")

    @selenium_test
    @managed_history
    def test_dataset_state_deferred(self):
        self.history_panel_create_new()
        history_id = self.current_history_id()
        self.dataset_populator.create_contents_from_store(
            history_id,
            store_dict=deferred_hda_model_store_dict(),
        )
        # regression after 3/24/2022 - explicit refresh now required.
        self.home()
        self.history_panel_wait_for_hid_state(FIRST_HID, state="deferred", allowed_force_refreshes=1)
        self.history_panel_click_item_title(hid=FIRST_HID, wait=True)
        self.screenshot("history_panel_dataset_deferred")
        # Next if is a hack for recent changes to beta history...
        # https://github.com/galaxyproject/galaxy/pull/13477/files#r823842897
        self._assert_downloadable(FIRST_HID, is_downloadable=False)

        self.history_panel_item_view_dataset_details(FIRST_HID)
        self.screenshot("dataset_details_deferred")
        details = self.components.dataset_details
        assert details.deferred_source_uri.wait_for_text() == TEST_SOURCE_URI

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
            expected_buttons = ["display", "edit", "delete"]
        self._assert_buttons(hid, expected_buttons)

    def _assert_action_buttons(self, hid, expected_buttons=None):
        if expected_buttons is None:
            expected_buttons = ["info", "download"]
        self._assert_buttons(hid, expected_buttons)

    def _assert_downloadable(self, hid, is_downloadable=True):
        item = self.history_panel_item_component(hid=hid)
        item.dataset_operations_dropdown.wait_for_and_click()
        item.info_button.wait_for_visible()
        if is_downloadable:
            assert item.download_button.is_displayed
        else:
            item.download_button.assert_absent_or_hidden()

        # close menu...
        item.dataset_operations_dropdown.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    def _assert_buttons(self, hid, expected_buttons):
        # TODO: Useful but unmigrated test from legacy history
        # item = self.history_panel_item_component(hid=hid)
        # for expected_button in expected_buttons:
        #    button = item[f"{expected_button}_button"]
        #    self.assert_tooltip_text(button.wait_for_visible(), BUTTON_TOOLTIPS[expected_button])'''
        return

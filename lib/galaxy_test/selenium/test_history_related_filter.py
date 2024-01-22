from .framework import (
    selenium_test,
    SeleniumTestCase,
)

PASTED_CONTENT = "this is pasted"
CURRENT_HID = 1
RELATED_HID = 2
UNRELATED_HID = 3


class TestHistoryRelatedFilter(SeleniumTestCase):
    @selenium_test
    def test_history_related_filter(self):
        self.register()
        # upload (current) dataset to get related item for
        self.perform_upload_of_pasted_content(PASTED_CONTENT)
        self.history_panel_wait_for_hid_ok(CURRENT_HID)
        # create related item through a tool
        self.tool_open("cat")
        self.tool_form_execute()
        self.history_panel_wait_for_hid_ok(RELATED_HID)
        # create an item unrelated to other items
        self.perform_upload_of_pasted_content(PASTED_CONTENT)
        self.history_panel_wait_for_hid_ok(UNRELATED_HID)

        # test related filter on current item using button: only current and related items show
        current_hda = self.history_panel_click_item_title(CURRENT_HID, wait=True)
        current_hda.highlight_button.wait_for_and_click()
        unrelated_hda = self.history_panel_item_component(hid=UNRELATED_HID)
        unrelated_hda.assert_absent_or_hidden()

        # test related filter on unrelated item using filterText: only unrelated item shows
        filter_element = self.history_element(
            attribute_value="filter text input", scope=".content-operations-filters"
        ).wait_for_and_click()
        initial_value = filter_element.get_attribute("value")
        assert initial_value == f"related:{CURRENT_HID}", initial_value
        self.history_element(attribute_value="reset query", scope=".content-operations-filters").wait_for_and_click()
        filter_element.send_keys(f"related:{UNRELATED_HID}")
        current_hda.wait_for_absent()

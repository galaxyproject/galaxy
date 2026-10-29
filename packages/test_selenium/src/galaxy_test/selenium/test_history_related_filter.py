from .framework import (
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity

PASTED_CONTENT = "this is pasted"
CURRENT_HID = 1
RELATED_HID = 2
UNRELATED_HID = 3


class TestHistoryRelatedFilter(SeleniumTestCase, UsesUploadActivity):
    @selenium_test
    def test_history_related_filter(self):
        self.register()
        # upload (current) dataset to get related item for
        self.upload_context("paste-content").stage_paste_content(PASTED_CONTENT).start()
        self.history_panel_wait_for_hid_ok(CURRENT_HID)
        # create related item through a tool
        self.tool_open("cat")
        self.tool_form_execute()
        self.history_panel_wait_for_hid_ok(RELATED_HID)
        # create an item unrelated to other items
        self.upload_context("paste-content").stage_paste_content(PASTED_CONTENT).start()
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

    @selenium_test
    def test_history_related_filter_copied_history(self):
        self.register()
        history_id = self.current_history_id()
        current_hda = self.dataset_populator.new_dataset(history_id, content=PASTED_CONTENT, wait=True)
        self.dataset_populator.run_tool("cat", {"input1": {"src": "hda", "id": current_hda["id"]}}, history_id)
        self.dataset_populator.new_dataset(history_id, content=PASTED_CONTENT)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        # jobs reference the original datasets, not the copies
        copied_history_id = self.dataset_populator.copy_history(history_id).json()["id"]
        self.get(f"histories/view?id={copied_history_id}")
        self.components.history_view.switch_to_history.wait_for_and_click()
        self.history_panel_wait_for_hid_ok(UNRELATED_HID)

        current_hda = self.history_panel_click_item_title(CURRENT_HID, wait=True)
        current_hda.highlight_button.wait_for_and_click()
        self.history_panel_item_component(hid=UNRELATED_HID).wait_for_absent_or_hidden()
        self.history_panel_item_component(hid=RELATED_HID).wait_for_visible()

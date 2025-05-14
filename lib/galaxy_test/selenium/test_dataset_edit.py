from galaxy.selenium.axe_results import FORMS_VIOLATIONS
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)

TEST_ANNOTATION = "my cool annotation"
TEST_INFO = "my cool info"


class TestHistoryPanel(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_history_dataset_rename(self):
        original_name = "1.txt"
        new_name = "newname.txt"

        history_entry = self.perform_single_upload(self.get_filename(original_name))
        hid = history_entry.hid
        self.wait_for_history()
        self.history_panel_wait_for_hid_ok(hid)
        self.history_panel_item_edit(hid=hid)
        edit_dataset_attributes = self.components.edit_dataset_attributes
        name_component = edit_dataset_attributes.name_input
        assert name_component.wait_for_value() == original_name
        edit_dataset_attributes._.assert_no_axe_violations_with_impact_of_at_least(
            "critical", excludes=FORMS_VIOLATIONS
        )
        name_component.wait_for_and_clear_and_send_keys(new_name)
        edit_dataset_attributes.save_button.wait_for_and_click()
        edit_dataset_attributes.alert.wait_for_visible()

        # assert success message, name updated in form and in history panel
        assert edit_dataset_attributes.alert.has_class("alert-success")
        assert name_component.wait_for_value() == new_name
        assert self.history_panel_item_component(hid=hid).name.wait_for_text() == new_name

    @selenium_test
    @managed_history
    def test_history_dataset_update_annotation_and_info(self):
        history_entry = self.perform_single_upload(self.get_filename("1.txt"))
        hid = history_entry.hid
        self.wait_for_history()
        self.history_panel_wait_for_hid_ok(hid)
        self.history_panel_item_edit(hid=hid)
        edit_dataset_attributes = self.components.edit_dataset_attributes
        annotation_component = edit_dataset_attributes.annotation_input
        annotation_component.wait_for_and_clear_and_send_keys(TEST_ANNOTATION)

        info_component = edit_dataset_attributes.info_input
        info_component.wait_for_and_clear_and_send_keys(TEST_INFO)

        edit_dataset_attributes.save_button.wait_for_and_click()
        edit_dataset_attributes.alert.wait_for_visible()

        # assert success message, name updated in form and in history panel
        assert edit_dataset_attributes.alert.has_class("alert-success")

        # reopen and check that attributes are updated
        self.home()
        self.history_panel_item_edit(hid=hid)

        assert annotation_component.wait_for_value() == TEST_ANNOTATION
        assert info_component.wait_for_value() == TEST_INFO

    @selenium_test
    @managed_history
    def test_history_dataset_auto_detect_datatype(self):
        expected_datatype = "txt"
        provided_datatype = "tabular"
        history_entry = self.perform_single_upload(self.get_filename("1.txt"), ext=provided_datatype)
        hid = history_entry.hid
        self.wait_for_history()
        self.history_panel_wait_for_hid_ok(hid)
        self.history_panel_item_edit(hid=hid)
        edit_dataset_attributes = self.components.edit_dataset_attributes
        datatypes_tab = edit_dataset_attributes.datatypes_tab
        datatype_component = edit_dataset_attributes.datatype_dropdown
        datatypes_tab.wait_for_and_click()
        assert datatype_component.wait_for_text() == provided_datatype

        # click auto detect datatype button
        edit_dataset_attributes.auto_detect_datatype_button.wait_for_and_click()
        edit_dataset_attributes.alert.wait_for_visible()

        assert edit_dataset_attributes.alert.has_class("alert-success")

        # reopen and check that datatype is updated
        self.home()
        self.history_panel_wait_for_hid_ok(hid)
        self.history_panel_item_edit(hid=hid)
        datatypes_tab.wait_for_and_click()

        assert datatype_component.wait_for_text() == expected_datatype

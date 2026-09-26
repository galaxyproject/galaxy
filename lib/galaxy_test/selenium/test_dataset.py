from galaxy.selenium.axe_results import FORMS_VIOLATIONS
from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity

TEST_ANNOTATION = "my cool annotation"
TEST_INFO = "my cool info"


class TestDataset(UsesUploadActivity, SeleniumTestCase):
    ensure_registered = True

    def _upload_single_file(self, test_path, ext=None):
        before_latest_history_item = self.latest_history_entry()
        uploader = self.upload_context("local-file")
        item = uploader.stage_local_file(test_path)
        if ext is not None:
            item.set_extension(ext)
        uploader._start_and_wait_for_uploaded_hids()
        after_latest_history_item = self.latest_history_entry()
        assert after_latest_history_item
        if before_latest_history_item is not None:
            assert before_latest_history_item.id != after_latest_history_item.id
        return after_latest_history_item

    @selenium_test
    @managed_history
    def test_history_dataset_display_text(self):
        original_name = "1.txt"

        history_entry = self._upload_single_file(self.get_filename(original_name))
        hid = history_entry.hid
        self.wait_for_history()
        self.history_panel_wait_for_hid_ok(hid)
        self.display_dataset(hid=hid)

        dataset_display = self.components.dataset_display.container
        dataset_display.wait_for_visible()

        with self.in_frame():
            text = self.components.dataset_display.content.wait_for_text()
            assert "chr1    4225    19670" in text

    @selenium_test
    @managed_history
    def test_history_dataset_display_tabular_loads_chunks_on_scroll(self):
        # About three of the server's 64 KiB display chunks; wide rows keep the table small enough for axe.
        content = "".join(f"{i}\t{'x' * 240}\n" for i in range(800))
        hda = self.dataset_populator.new_dataset(
            self.current_history_id(), content=content, file_type="tabular", wait=True
        )
        self.history_panel_wait_for_hid_ok(hda["hid"])
        self.display_dataset(hid=hda["hid"])

        dataset_display = self.components.dataset_display
        dataset_display.tabular_row(index=1).wait_for_visible()
        rows = dataset_display.tabular_rows.all()
        initial_rows = len(rows)
        assert 0 < initial_rows < 800

        self.scroll_into_view(rows[-1])
        dataset_display.tabular_row(index=initial_rows + 1).wait_for_present()

    @selenium_test
    @managed_history
    def test_history_dataset_rename(self):
        original_name = "1.txt"
        new_name = "newname.txt"

        history_entry = self._upload_single_file(self.get_filename(original_name))
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

        # The success alert can appear before the asynchronous history refresh finishes.
        @retry_assertion_during_transitions
        def assert_history_name_updated():
            assert self.history_panel_item_component(hid=hid).name.wait_for_text() == new_name

        assert_history_name_updated()

    @selenium_test
    @managed_history
    def test_history_dataset_update_annotation_and_info(self):
        history_entry = self._upload_single_file(self.get_filename("1.txt"))
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
        history_entry = self._upload_single_file(self.get_filename("1.txt"), ext=provided_datatype)
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

from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class DatasetSourceTransformSeleniumIntegrationTestCase(PosixFileSourceSetup, SeleniumIntegrationTestCase):
    ensure_registered = True
    include_test_data_dir = True

    @selenium_test
    def test_displaying_source_transformations_posixlines(self):
        history_id = self.current_history_id()
        item = {
            "src": "url",
            "url": "gxfiles://testdatafiles/simple_line_no_newline.txt",
            "ext": "txt",
            "to_posix_lines": True,
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        actions = self.dataset_populator.get_history_dataset_source_transform_actions(
            history_id, dataset=output, assert_ok=True
        )
        assert actions == {"to_posix_lines"}
        details = self._display_first_hid_details()
        transform_element = details.transform_action(action="to_posix_lines").wait_for_visible()
        self.assert_tooltip_text_contains(transform_element, "newline characters in text files")
        self.screenshot("dataset_details_source_transform_to_posix_lines")

    @selenium_test
    def test_displaying_source_transformations_spaces_to_tabs(self):
        history_id = self.current_history_id()
        item = {
            "src": "url",
            "url": "gxfiles://testdatafiles/simple_line_x2_windows.txt",
            "ext": "txt",
            "to_posix_lines": True,
            "space_to_tab": True,
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        actions = self.dataset_populator.get_history_dataset_source_transform_actions(
            history_id, dataset=output, assert_ok=True
        )
        assert actions == {"spaces_to_tabs", "to_posix_lines"}
        details = self._display_first_hid_details()
        transform_element = details.transform_action(action="spaces_to_tabs").wait_for_visible()
        self.assert_tooltip_text_contains(transform_element, "referenced data source to tabular data", click_away=False)
        self.screenshot("dataset_details_source_transform_spaces_to_tabs")

    @selenium_test
    def test_displaying_source_transformations_grooming(self):
        history_id = self.current_history_id()
        item = {
            "src": "url",
            "url": "gxfiles://testdatafiles/qname_sorted.bam",
            "ext": "bam",
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        actions = self.dataset_populator.get_history_dataset_source_transform_actions(
            history_id, dataset=output, assert_ok=True
        )
        assert actions == {"datatype_groom"}
        details = self._display_first_hid_details()
        transform_element = details.transform_action(action="datatype_groom").wait_for_visible()
        self.assert_tooltip_text_contains(transform_element, "sorted", click_away=False)
        self.screenshot("dataset_details_source_transform_bam_grooming")
        self.click_center()
        self.assert_tooltip_text_contains(
            transform_element, "Galaxy applied datatype specific cleaning of the supplied data", click_away=False
        )

    def _display_first_hid_details(self):
        self.home()
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_click_item_title(hid=1, wait=True)
        self.history_panel_item_view_dataset_details(1)
        return self.components.dataset_details

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()


class DatasetSourceTransformInModelStoreSeleniumIntegrationTestCase(DatasetSourceTransformSeleniumIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["metadata_strategy"] = "extended"

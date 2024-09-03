from galaxy_test.base.populators import (
    skip_without_datatype,
    skip_without_visualization_plugin,
)
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestVisualizations(SeleniumTestCase):
    ensure_registered = True

    @skip_without_datatype("png")
    @skip_without_visualization_plugin("annotate_image")
    @selenium_test
    @managed_history
    def test_charts_image_annotate(self):
        hid = 1
        self.perform_upload(self.get_filename("454Score.png"))
        self.wait_for_history()
        dataset_component = self.history_panel_click_item_title(hid, wait=True)
        dataset_component.visualize_button.wait_for_and_click()

        self.components.visualization.plugin_item(id="annotate_image").wait_for_visible()
        self.screenshot("visualization_plugins_png")
        self.components.visualization.plugin_item(id="annotate_image").wait_for_and_click()

        with self.visualization_panel():
            self.wait_for_selector("#image-annotate")
            self.screenshot("visualization_plugin_charts_image_annotate")

    @managed_history
    @selenium_test
    @skip_without_visualization_plugin("nvd3_bar")
    def test_charts_nvd3_bar(self):
        hid = 1
        self.perform_upload(self.get_filename("1.sam"))
        dataset_component = self.history_panel_click_item_title(hid, wait=True)
        dataset_component.visualize_button.wait_for_and_click()

        self.components.visualization.plugin_item(id="nvd3_bar").wait_for_visible()
        self.screenshot("visualization_plugins_sam")
        self.components.visualization.plugin_item(id="nvd3_bar").wait_for_and_click()

        with self.visualization_panel():
            self.wait_for_selector("g.nvd3")
            self.screenshot("visualization_plugin_charts_nvd3_bar_landing")

    @managed_history
    @selenium_test
    @skip_without_visualization_plugin("h5web")
    def test_charts_h5web(self):
        hid = 1
        self.perform_upload(self.get_filename("chopper.h5"))
        self.history_panel_wait_for_hid_ok(hid)
        dataset_component = self.history_panel_click_item_title(hid, wait=True)
        dataset_component.visualize_button.wait_for_and_click()

        self.components.visualization.plugin_item(id="h5web").wait_for_visible()
        self.screenshot("visualization_plugins_h5")
        self.components.visualization.plugin_item(id="h5web").wait_for_and_click()

        with self.visualization_panel():
            # Look for the h5web-explorer-tree identifier to verify it loads.
            self.wait_for_selector("#h5web-explorer-tree")
            self.screenshot("visualization_plugin_charts_h5web_landing")

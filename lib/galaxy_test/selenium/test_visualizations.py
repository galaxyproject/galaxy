from galaxy_test.base.populators import (
    skip_without_datatype,
    skip_without_visualization_plugin,
)
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestVisualizations(SeleniumTestCase):

    @skip_without_datatype("png")
    @skip_without_visualization_plugin("annotate_image")
    @selenium_test
    def test_charts_image_annotate(self):
        hid = 1
        self.perform_upload(self.get_filename("454Score.png"))
        self.history_panel_wait_for_hid_state(hid, state="ok")
        self.show_dataset_visualizations(hid)

        self.components.visualization.matched_plugin(id="annotate_image").wait_for_visible()
        self.screenshot("visualization_plugins_png")
        self.components.visualization.matched_plugin(id="annotate_image").wait_for_and_click()

        with self.visualization_panel():
            self.wait_for_selector("#image-annotate")
            self.screenshot("visualization_plugin_charts_image_annotate")

    @selenium_test
    @skip_without_visualization_plugin("h5web")
    def test_charts_h5web(self):
        hid = 1
        self.perform_upload(self.get_filename("chopper.h5"))
        self.history_panel_wait_for_hid_state(hid, state="ok")
        self.show_dataset_visualizations(hid)

        self.components.visualization.matched_plugin(id="h5web").wait_for_visible()
        self.screenshot("visualization_plugins_h5")
        self.components.visualization.matched_plugin(id="h5web").wait_for_and_click()

        with self.visualization_panel():
            # Look for the h5web-explorer-tree identifier to verify it loads.
            self.wait_for_selector("#h5web-explorer-tree")
            self.screenshot("visualization_plugin_charts_h5web_landing")

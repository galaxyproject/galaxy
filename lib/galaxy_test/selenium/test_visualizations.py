from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestVisualizations(SeleniumTestCase):
    @selenium_test
    def test_charts_framework(self):
        self.register()
        self.perform_upload(self.get_filename("1.sam"))
        self.history_panel_wait_for_hid_ok(1)
        dataset_component = self.history_panel_click_item_title(1, wait=True)
        dataset_component.visualize_button.wait_for_and_click()

        self.components.visualization.plugin_item(id="nvd3_bar").wait_for_and_click()

        with self.main_panel():
            self.wait_for_selector("g.nvd3")
            self.screenshot("test_charts_framework -- nvd3_bar")

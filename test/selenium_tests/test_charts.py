from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)

CHARTS_VISUALIZATION_NAME = "Charts"


class ChartsTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    @managed_history
    def test_jupyter_session(self):
        self.perform_upload(self.get_filename("2.tabular"))
        self.wait_for_history()
        self.history_panel_ensure_showing_item_details(1)
        self.history_panel_item_click_visualization_menu(1)
        self.ensure_visualization_available(1, CHARTS_VISUALIZATION_NAME)
        self.history_panel_item_click_visualization(1, CHARTS_VISUALIZATION_NAME)
        with self.main_panel():
            self.components.charts.visualize_button.wait_for_and_click()
            self.components.charts.viewport_canvas.wait_for_visible()

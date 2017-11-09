from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)

JUPYTER_VISUALIZATION_NAME = "Jupyter"


class JupyterTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    @managed_history
    def test_jupyter_session(self):
        self.perform_upload(self.get_filename("1.txt"))
        self.perform_upload(self.get_filename("selenium-test-notebook.ipynb"))
        self.wait_for_history()
        self.history_panel_ensure_showing_item_details(2)
        self.history_panel_item_click_visualization_menu(2)
        self.ensure_visualization_available(2, JUPYTER_VISUALIZATION_NAME)
        self.history_panel_item_click_visualization(2, JUPYTER_VISUALIZATION_NAME)
        with self.main_panel():
            viz_iframe = self.wait_for_selector("body iframe", wait_type=self.wait_types.GIE_SPAWN)
            try:
                self.driver.switch_to.frame(viz_iframe)
                self.wait_for_selector("ul.nav")
                lis = self.driver.find_elements_by_css_selector("ul.nav li.dropdown")
                cell_li = None
                for li in lis:
                    if li.text == "Cell":
                        cell_li = li
                        break
                cell_li.click()
                self.wait_for_and_click_selector("ul#cell_menu li#run_all_cells")
            finally:
                self.driver.switch_to.default_content()

        # TODO: wait on something in the notebook instead of sleeping so long.
        self.sleep_for(wait_type=self.wait_types.JOB_COMPLETION)
        self.history_panel_refresh_click()

        # Re-running notebook should publish two new things to the history.
        self.history_panel_wait_for_hid_ok(3)
        self.history_panel_wait_for_hid_ok(4)

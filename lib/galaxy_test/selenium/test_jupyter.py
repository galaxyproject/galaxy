from galaxy_test.base.populators import flakey
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)

JUPYTER_VISUALIZATION_NAME = "Jupyter"


class JupyterTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    @flakey
    @managed_history
    def test_jupyter_launch(self):
        self._stage_test_data_and_launch()
        with self.main_panel():
            self.components.gies.spinner.wait_for_absent(wait_type=self.wait_types.GIE_SPAWN)
            viz_iframe = self.components.gies.iframe.wait_for_visible(wait_type=self.wait_types.GIE_SPAWN)
            try:
                self.driver.switch_to.frame(viz_iframe)
                self.components.gies.jupyter.body.wait_for_visible()
                trusted_element = self.components.gies.jupyter.trusted_notification.wait_for_visible()
                assert trusted_element.text == "Trusted"
            finally:
                self.driver.switch_to.default_content()

    @selenium_test
    @flakey
    @managed_history
    def test_jupyter_interaction(self):
        self._stage_test_data_and_launch()
        with self.main_panel():
            self.components.gies.spinner.wait_for_absent(wait_type=self.wait_types.GIE_SPAWN)
            viz_iframe = self.components.gies.iframe.wait_for_visible(wait_type=self.wait_types.GIE_SPAWN)
            try:
                self.driver.switch_to.frame(viz_iframe)
                self.components.gies.jupyter.body.wait_for_visible()
                self.wait_for_selector("ul.nav")
                li_links = self.driver.find_elements_by_css_selector("ul.nav li.dropdown a.dropdown-toggle")
                cell_li = None
                found_li_texts = []
                for li_link in li_links:
                    li_text = li_link.text
                    found_li_texts.append(li_text)
                    if li_link.text == "Cell":
                        cell_li = li_link
                        break
                if cell_li is None:
                    raise Exception(f"Failed to find 'Cell' drop down menu, found menu options {found_li_texts}")
                cell_li.click()
                self.wait_for_and_click_selector("ul#cell_menu li#run_all_cells")
            finally:
                self.driver.switch_to.default_content()

        self.sleep_for(wait_type=self.wait_types.JOB_COMPLETION)
        self.history_panel_refresh_click()

        # Re-running notebook should publish two new things to the history.
        self.history_panel_wait_for_hid_ok(3)
        self.history_panel_wait_for_hid_ok(4)

    def _stage_test_data_and_launch(self):
        self.perform_upload(self.get_filename("1.txt"))
        self.perform_upload(self.get_filename("selenium-test-notebook.ipynb"))
        self.wait_for_history()
        self.history_panel_ensure_showing_item_details(2)
        self.history_panel_item_click_visualization_menu(2)
        self.ensure_visualization_available(2, JUPYTER_VISUALIZATION_NAME)
        self.history_panel_item_click_visualization(2, JUPYTER_VISUALIZATION_NAME)
        # Wait for the link to update the content to main panel, without this sleep I think
        # sometimes Selenium is waiting in the previous page (presumably Galaxy's welcome).
        self.sleep_for(wait_type=self.wait_types.UX_TRANSITION)

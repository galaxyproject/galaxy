from galaxy_test.base.populators import (
    skip_without_datatype,
    skip_without_visualization_plugin,
)
from .framework import (
    managed_history,
    selenium_only,
    selenium_test,
    SeleniumTestCase,
)

HG18_DBKEY_TEXT = "Human Mar. 2006 (NCBI36/hg18) (hg18)"


class TestVisualizationsAnonymous(SeleniumTestCase):

    @skip_without_datatype("png")
    @skip_without_visualization_plugin("annotate_image")
    @selenium_test
    def test_charts_image_annotate(self):
        hid = 1
        self.perform_upload(self.get_filename("454Score.png"))
        self.history_panel_wait_for_hid_state(hid, state="ok")

        self.show_dataset_visualization(
            hid, visualization_id="annotate_image", screenshot_name="visualization_plugins_png"
        )

        with self.visualization_panel():
            self.wait_for_selector("#image-annotate")
            self.screenshot("visualization_plugin_charts_image_annotate")

    @selenium_only("Not yet migrated to support Playwright backend - need to implement shadow DOM absractions")
    @selenium_test
    @skip_without_visualization_plugin("tabulator")
    def test_charts_tabulator(self):
        hid = 1
        self.perform_upload(self.get_filename("1.tabular"))
        self.history_panel_wait_for_hid_state(hid, state="ok")
        self.show_dataset_visualization(
            hid, visualization_id="tabulator", screenshot_name="visualization_plugins_tabulator"
        )

        with self.visualization_panel():
            self.wait_for_selector(".tabulator-table")
            self.screenshot("visualization_plugin_tabulator_landing")

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @skip_without_visualization_plugin("h5web")
    def test_charts_h5web(self):
        hid = 1
        self.perform_upload(self.get_filename("chopper.h5"))
        self.history_panel_wait_for_hid_state(hid, state="ok")
        self.show_dataset_visualization(hid, visualization_id="h5web", screenshot_name="visualization_plugins_h5")

        with self.visualization_panel():
            # Look for the h5web-explorer-tree identifier to verify it loads.
            self.wait_for_selector("#h5web-explorer-tree")
            self.screenshot("visualization_plugin_charts_h5web_landing")


class TestVisualizations(SeleniumTestCase):
    ensure_registered = True

    @selenium_only("Not yet migrated to support Playwright backend - need to implement shadow DOM absractions")
    @selenium_test
    @managed_history
    @skip_without_visualization_plugin("igv")
    def test_igv_loads_correct_genome(self):
        hid = 1
        self.perform_upload(self.get_filename("1.bed"))
        self.history_panel_wait_for_hid_state(hid, state="ok")
        self.show_dataset_visualization(hid, visualization_id="igv", screenshot_name="visualization_plugins_igv")

        with self.visualization_panel():
            self._wait_for_igv_container()
            igv = self.components.igv
            igv.confirm_button.wait_for_and_click()
            igv.expand_button.wait_for_and_click()
            igv.settings_tab.wait_for_and_click()
            igv.default_genome.wait_for_present()
            self.screenshot("visualization_plugin_igv_default_genome")

        dataset_component = self.history_panel_ensure_showing_item_details(hid)
        dataset_component.dbkey.wait_for_and_click()
        self.edit_dataset_dbkey(HG18_DBKEY_TEXT)
        self.show_dataset_visualization(hid, visualization_id="igv")

        with self.visualization_panel():
            self._wait_for_igv_container()
            igv = self.components.igv
            igv.confirm_button.assert_absent_or_hidden()
            igv.expand_button.wait_for_and_click()
            igv.settings_tab.wait_for_and_click()
            igv.current_genome.wait_for_present()
            self.screenshot("visualization_plugin_igv_current_genome")

            igv.name_input.wait_for_and_clear_aggressive_and_send_keys("igv with hg18")
            igv.save_button.wait_for_and_click()
            self.sleep_for(self.wait_types.UX_TRANSITION)

        self.navigate_to_saved_visualizations()


    def _wait_for_igv_container(self):
        igv = self.components.igv
        self.sleep_for(self.wait_types.UX_TRANSITION)
        element = igv.shadow_host.wait_for_present()
        shadow_root = element.shadow_root

        igv_root_container = self.navigation.igv.selectors._
        shadow_root.find_element(*igv_root_container.component_locator)

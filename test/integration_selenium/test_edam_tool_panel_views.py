from galaxy.selenium.navigates_galaxy import retry_during_transitions
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestEdamToolPanelViewsSeleniumIntegration(SeleniumIntegrationTestCase):
    ensure_registered = True  # to test workflow editor

    @selenium_test
    def test_basic_navigation(self):
        tool_panel = self.components.tool_panel
        tool_panel.views_button.wait_for_and_click()
        tool_panel.views_menu_item(panel_id="ontology:edam_operations").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self._assert_displaying_edam_operations()

        # reload page and ensure the edam operations are still being displayed.
        self.home()
        tool_panel.views_button.wait_for_visible()
        self._assert_displaying_edam_operations()
        self.screenshot("tool_panel_view_edam_landing")

        # navigate to workflow editor and make sure this is still enabled...
        annotation = "tool panel test"
        self.workflow_create_new(annotation=annotation)

        editor = self.components.workflow_editor
        editor.canvas_body.wait_for_visible()
        editor.tool_menu.wait_for_visible()
        self._assert_displaying_edam_operations()
        self.screenshot("tool_panel_view_edam_workflow_editor")

    @retry_during_transitions
    def _assert_displaying_edam_operations(self):
        tool_panel = self.components.tool_panel
        tool_panel.toolbox.wait_for_visible()
        labels = tool_panel.panel_labels.all()
        assert len(labels) > 0
        label0 = labels[0]
        assert label0.text.strip().startswith("ANALYSIS")

from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class TestEdamToolPanelViewsSelenium(SeleniumTestCase):
    ensure_registered = True  # to test workflow editor

    @selenium_test
    def test_basic_navigation(self):
        self.swap_to_tool_panel_edam_operations()
        self._assert_displaying_edam_operations()

        # reload page and ensure the edam operations are still being displayed.
        self.home()
        tool_panel = self.components.tool_panel
        tool_panel.views_button.wait_for_visible()
        self._assert_displaying_edam_operations()
        self.screenshot("tool_panel_view_edam_landing")

        # navigate to workflow editor and make sure this is still enabled...
        annotation = "tool panel test"
        self.workflow_create_new(annotation=annotation)

        editor = self.components.workflow_editor
        editor.canvas_body.wait_for_visible()
        self.open_toolbox()
        self._assert_displaying_edam_operations()
        self.screenshot("tool_panel_view_edam_workflow_editor")

    @retry_assertion_during_transitions
    def _assert_displaying_edam_operations(self):
        tool_panel = self.components.tool_panel
        tool_panel.toolbox.wait_for_visible()
        tool_panel.edam_title.wait_for_visible()
        labels = tool_panel.panel_labels.all()
        assert len(labels) > 0
        label0 = labels[0]
        assert label0.text.strip().startswith("ANALYSIS")

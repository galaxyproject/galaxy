from ._workflow_fixtures import (
    WORKFLOW_SIMPLE_CAT_TWICE,
    WORKFLOW_WITH_INVALID_STATE,
    WORKFLOW_WITH_OLD_TOOL_VERSION,
)
from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase
)


class WorkflowEditorTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_build_workflow(self):
        name = "test_edit_nam"
        self.workflow_create_new(name=name)
        element = self.wait_for_selector("#edit-attributes #workflow-name")
        assert name in element.text, element.text

    @selenium_test
    def test_data_input(self):
        self.workflow_create_new()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        menu = self.wait_for_selector(".toolMenu")
        self.sleep_for(self.wait_types.UX_RENDER)
        inputs_section = menu.find_element_by_css_selector("#title___workflow__inputs__")
        inputs_link = inputs_section.find_element_by_css_selector("a span")
        inputs_link.click()
        self.wait_for_selector_visible("#__workflow__inputs__ .toolTitle")
        input_links = self.driver.find_elements_by_css_selector("#__workflow__inputs__ .toolTitle a")
        input_links[0].click()
        self.screenshot("workflow_editor_data_input")
        # TODO: verify box is highlighted and side panel is a form describing input.
        # More work needs to be done to develop testing abstractions for doing these things.

    @selenium_test
    def test_save_as(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_editor_edit_menu")
        self.workflow_editor_click_option("Save As")

    @selenium_test
    def test_editor_tool_upgrade_message(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(WORKFLOW_WITH_OLD_TOOL_VERSION, exact_tools=True)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        self.assert_modal_has_text("Using version '0.2' instead of version '0.0.1'")
        self.screenshot("workflow_editor_tool_upgrade")

    @selenium_test
    def test_editor_invalid_tool_state(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(WORKFLOW_WITH_INVALID_STATE, exact_tools=True)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        self.assert_modal_has_text("Using version '0.2' instead of version '0.0.1'")
        self.assert_modal_has_text("Using default: '1'")
        self.screenshot("workflow_editor_invalid_state")

    @selenium_test
    def test_missing_tools(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  - id: input1
steps:
  - tool_id: missing
    label: first_cat
    state:
      foo: bar
""")
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        self.assert_modal_has_text("Tool is not installed")
        self.screenshot("workflow_editor_missing_tool")

    def workflow_create_new(self, name=None, annotation=None):
        self.workflow_index_open()
        self.click_button_new_workflow()
        form_element = self.driver.find_element_by_id("submit")
        name = name or self._get_random_name()
        annotation = annotation or self._get_random_name()
        inputs = self.driver.find_elements_by_class_name("ui-input")
        inputs[0].send_keys(name)
        inputs[1].send_keys(annotation)
        form_element.click()

    @retry_assertion_during_transitions
    def assert_modal_has_text(self, expected_text):
        modal_element = self.wait_for_selector_visible(self.modal_body_selector())
        text = modal_element.text
        assert expected_text in text, "Failed to find expected text [%s] in modal text [%s]" % (expected_text, text)

import time

from .framework import (
    selenium_test,
    SeleniumTestCase
)

from ._workflow_fixtures import (
    WORKFLOW_SIMPLE_CAT_TWICE,
    WORKFLOW_WITH_OLD_TOOL_VERSION,
    WORKFLOW_WITH_INVALID_STATE,
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
        menu = self.wait_for_selector(".toolMenu")
        time.sleep(1)
        inputs_section = menu.find_element_by_css_selector("#title___workflow__inputs__")
        inputs_link = inputs_section.find_element_by_css_selector("a span")
        inputs_link.click()
        self.wait_for_selector_visible("#__workflow__inputs__ .toolTitle")
        input_links = self.driver.find_elements_by_css_selector("#__workflow__inputs__ .toolTitle a")
        input_links[0].click()
        # TODO: verify box is highlighted and side panel is a form describing input.
        # More work needs to be done to develop testing abstractions for doing these things.

    @selenium_test
    def test_save_as(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        time.sleep(1)
        self.workflow_editor_click_option("Save As")

    @selenium_test
    def test_editor_tool_upgrade_message(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(WORKFLOW_WITH_OLD_TOOL_VERSION, exact_tools=True)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        time.sleep(.5)
        modal_element = self.wait_for_selector_visible(self.modal_body_selector())
        text = modal_element.text
        assert "Using version '0.2' instead of version '0.0.1'" in text, text

    @selenium_test
    def test_editor_invalid_tool_state(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(WORKFLOW_WITH_INVALID_STATE, exact_tools=True)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        time.sleep(.5)
        modal_element = self.wait_for_selector_visible(self.modal_body_selector())
        text = modal_element.text
        assert "Using version '0.2' instead of version '0.0.1'" in text, text
        assert "Using default: '1'" in text, text

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
        time.sleep(.5)
        modal_element = self.wait_for_selector_visible(self.modal_body_selector())
        text = modal_element.text
        assert "Tool is not installed" in text, text

    def workflow_create_new(self, name=None, annotation=None):
        self.workflow_index_open()
        self.click_button_new_workflow()

        form_element = self.driver.find_element_by_css_selector("#center form")
        action = form_element.get_attribute("action")
        assert action.endswith("/workflow/create"), action

        name = name or self._get_random_name()
        annotation = annotation or self._get_random_name()
        self.fill(form_element, {
            'workflow_name': name,
            'workflow_annotation': annotation,
        })
        self.click_submit(form_element)

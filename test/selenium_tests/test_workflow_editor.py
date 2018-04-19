from base.workflow_fixtures import (
    WORKFLOW_NESTED_SIMPLE,
    WORKFLOW_SIMPLE_CAT_TWICE,
    WORKFLOW_SIMPLE_MAPPING,
    WORKFLOW_WITH_INVALID_STATE,
    WORKFLOW_WITH_OLD_TOOL_VERSION,
    WORKFLOW_WITH_OUTPUT_COLLECTION,
)

from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase
)


class WorkflowEditorTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_basics(self):
        editor = self.components.workflow_editor

        name = self.workflow_create_new()
        edit_name_element = self.components.workflow_editor.edit_name.wait_for_visible()
        assert name in edit_name_element.text, edit_name_element.text

        editor.canvas_body.wait_for_visible()
        editor.tool_menu.wait_for_visible()

        self.screenshot("workflow_editor_blank")

        self.components._.left_panel_drag.wait_for_visible()
        self.components._.left_panel_collapse.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)

        self.screenshot("workflow_editor_left_collapsed")

        self.components._.right_panel_drag.wait_for_visible()
        self.components._.right_panel_collapse.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)

        self.screenshot("workflow_editor_left_and_right_collapsed")

    @selenium_test
    def test_data_input(self):
        editor = self.components.workflow_editor

        name = self.workflow_create_new()
        editor.canvas_body.wait_for_visible()
        editor.tool_menu.wait_for_visible()
        editor.tool_menu_section_link(section_name="inputs").wait_for_and_click()
        editor.tool_menu_item_link(section_name="inputs", item_name="data_input").wait_for_and_click()
        self.screenshot("workflow_editor_data_input_new")
        editor.label_input.wait_for_and_send_keys("input1")
        editor.annotation_input.wait_for_and_send_keys("my cool annotation")
        editor.label_input.wait_for_and_click()  # Seems to help force the save of whole annotation.
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_editor_data_input_filled_in")
        self.workflow_editor_save_and_close()
        self.workflow_index_open_with_name(name)
        data_input_node = editor.node._(label="input1")
        data_input_node.title.wait_for_and_click()

        label = editor.label_input.wait_for_value()
        assert label == "input1", label
        assert editor.annotation_input.wait_for_value() == "my cool annotation"

        data_input_node.destroy.wait_for_and_click()
        data_input_node.wait_for_absent()
        self.screenshot("workflow_editor_data_input_deleted")

    @selenium_test
    def test_collection_input(self):
        editor = self.components.workflow_editor

        name = self.workflow_create_new()
        editor.canvas_body.wait_for_visible()
        editor.tool_menu.wait_for_visible()
        editor.tool_menu_section_link(section_name="inputs").wait_for_and_click()
        editor.tool_menu_item_link(section_name="inputs", item_name="data_collection_input").wait_for_and_click()
        self.screenshot("workflow_editor_data_input_collection_new")
        editor.label_input.wait_for_and_send_keys("input1")
        editor.annotation_input.wait_for_and_send_keys("my cool annotation")
        editor.label_input.wait_for_and_click()  # Seems to help force the save of whole annotation.
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_editor_data_input_collection_filled_in")
        self.workflow_editor_save_and_close()
        self.workflow_index_open_with_name(name)
        data_input_node = editor.node._(label="input1")
        data_input_node.title.wait_for_and_click()

        label = editor.label_input.wait_for_value()
        assert label == "input1", label
        assert editor.annotation_input.wait_for_value() == "my cool annotation"

        data_input_node.destroy.wait_for_and_click()
        data_input_node.wait_for_absent()
        self.screenshot("workflow_editor_data_input_deleted")

    @selenium_test
    def test_existing_connections(self):
        self.open_in_workflow_editor(WORKFLOW_SIMPLE_CAT_TWICE)

        editor = self.components.workflow_editor
        self.assert_connected("input1#output", "first_cat#input1")
        self.screenshot("workflow_editor_connection_simple")

        cat_node = editor.node._(label="first_cat")
        cat_input = cat_node.input_terminal(name="input1")
        cat_input.wait_for_and_click()
        editor.connector_destroy_callout.wait_for_visible()
        self.screenshot("workflow_editor_connection_callout")
        editor.connector_destroy_callout.wait_for_and_click()
        self.assert_not_connected("input1#output", "first_cat#input1")
        self.screenshot("workflow_editor_connection_destroyed")

        self.workflow_editor_connect("input1#output", "first_cat#input1", screenshot_partial="workflow_editor_connection_dragging")
        self.assert_connected("input1#output", "first_cat#input1")

    @selenium_test
    def test_rendering_output_collection_connections(self):
        self.open_in_workflow_editor(WORKFLOW_WITH_OUTPUT_COLLECTION)
        self.workflow_editor_maximize_center_pane()
        self.screenshot("workflow_editor_output_collections")

    @selenium_test
    def test_simple_mapping_connections(self):
        self.open_in_workflow_editor(WORKFLOW_SIMPLE_MAPPING)
        self.workflow_editor_maximize_center_pane()
        self.screenshot("workflow_editor_simple_mapping")
        self.assert_connected("input1#output", "cat#input1")
        self.assert_input_mapped("cat#input1")
        self.workflow_editor_destroy_connection("cat#input1")
        self.assert_input_not_mapped("cat#input1")
        self.assert_not_connected("input1#output", "cat#input1")
        self.workflow_editor_connect("input1#output", "cat#input1")
        self.assert_input_mapped("cat#input1")

    @selenium_test
    def test_rendering_simple_nested_workflow(self):
        self.open_in_workflow_editor(WORKFLOW_NESTED_SIMPLE)
        self.workflow_editor_maximize_center_pane()
        self.screenshot("workflow_editor_simple_nested")

    @selenium_test
    def test_save_as(self):
        name = self.workflow_upload_yaml_with_random_name(WORKFLOW_SIMPLE_CAT_TWICE)
        self.workflow_index_open()
        self.workflow_index_open_with_name(name)
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

    def workflow_editor_save_and_close(self):
        self.workflow_editor_click_option("Save")
        self.workflow_editor_click_option("Close")

    def workflow_editor_maximize_center_pane(self):
        self.components._.left_panel_collapse.wait_for_and_click()
        self.components._.right_panel_collapse.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    def workflow_editor_connect(self, source, sink, screenshot_partial=None):
        source_id, sink_id = self.workflow_editor_source_sink_terminal_ids(source, sink)
        source_element = self.driver.find_element_by_css_selector("#" + source_id)
        sink_element = self.driver.find_element_by_css_selector("#" + sink_id)

        ac = self.action_chains()
        ac = ac.move_to_element(source_element).click_and_hold()
        if screenshot_partial:
            ac = ac.move_to_element_with_offset(sink_element, -5, 0)
            ac.perform()
            self.sleep_for(self.wait_types.UX_RENDER)
            self.screenshot(screenshot_partial)
            ac = self.action_chains()

        ac = ac.move_to_element(sink_element).release().perform()

    def assert_connected(self, source, sink):
        source_id, sink_id = self.workflow_editor_source_sink_terminal_ids(source, sink)
        self.components.workflow_editor.connector_for(source_id=source_id, sink_id=sink_id).wait_for_visible()

    def assert_not_connected(self, source, sink):
        source_id, sink_id = self.workflow_editor_source_sink_terminal_ids(source, sink)
        self.components.workflow_editor.connector_for(source_id=source_id, sink_id=sink_id).wait_for_absent()

    def open_in_workflow_editor(self, yaml_content):
        name = self.workflow_upload_yaml_with_random_name(yaml_content)
        self.workflow_index_open()
        self.workflow_index_open_with_name(name)
        self.workflow_editor_click_option("Auto Re-layout")

    def workflow_editor_source_sink_terminal_ids(self, source, sink):
        editor = self.components.workflow_editor

        source_node_label, source_output = source.split("#", 1)
        sink_node_label, sink_input = sink.split("#", 1)

        source_node = editor.node._(label=source_node_label)
        sink_node = editor.node._(label=sink_node_label)

        source_node.wait_for_visible()
        sink_node.wait_for_visible()

        output_terminal = source_node.output_terminal(name=source_output)
        input_terminal = sink_node.input_terminal(name=sink_input)

        output_element = output_terminal.wait_for_visible()
        input_element = input_terminal.wait_for_visible()

        source_id = output_element.get_attribute("id")
        sink_id = input_element.get_attribute("id")

        return source_id, sink_id

    def workflow_editor_destroy_connection(self, sink):
        editor = self.components.workflow_editor

        sink_node_label, sink_input_name = sink.split("#", 1)
        sink_node = editor.node._(label=sink_node_label)
        sink_input = sink_node.input_terminal(name=sink_input_name)
        sink_input.wait_for_and_click()
        editor.connector_destroy_callout.wait_for_and_click()

    def assert_input_mapped(self, sink):
        editor = self.components.workflow_editor
        sink_node_label, sink_input_name = sink.split("#", 1)
        sink_node = editor.node._(label=sink_node_label)
        sink_mapping_icon = sink_node.input_mapping_icon(name=sink_input_name)
        sink_mapping_icon.wait_for_visible()

    def assert_input_not_mapped(self, sink):
        editor = self.components.workflow_editor
        sink_node_label, sink_input_name = sink.split("#", 1)
        sink_node = editor.node._(label=sink_node_label)
        sink_mapping_icon = sink_node.input_mapping_icon(name=sink_input_name)
        sink_mapping_icon.wait_for_absent_or_hidden()

    def workflow_index_open_with_name(self, name):
        self.workflow_index_open()
        self.workflow_index_search_for(name)
        self.workflow_index_click_option("Edit")

    def workflow_upload_yaml_with_random_name(self, content):
        workflow_populator = self.workflow_populator
        name = self._get_random_name()
        workflow_populator.upload_yaml_workflow(content, name=name)
        return name

    def workflow_create_new(self, annotation=None):
        self.workflow_index_open()
        self.click_button_new_workflow()
        form_element = self.driver.find_element_by_id("submit")
        name = self._get_random_name()
        annotation = annotation or self._get_random_name()
        inputs = self.driver.find_elements_by_class_name("ui-input")
        inputs[0].send_keys(name)
        inputs[1].send_keys(annotation)
        form_element.click()
        return name

    @retry_assertion_during_transitions
    def assert_modal_has_text(self, expected_text):
        modal_element = self.wait_for_selector_visible(self.modal_body_selector())
        text = modal_element.text
        assert expected_text in text, "Failed to find expected text [%s] in modal text [%s]" % (expected_text, text)

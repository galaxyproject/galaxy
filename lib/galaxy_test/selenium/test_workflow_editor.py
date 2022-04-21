import json

import yaml
from selenium.webdriver.common.keys import Keys

from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_NESTED_SIMPLE,
    WORKFLOW_OPTIONAL_TRUE_INPUT_COLLECTION,
    WORKFLOW_SELECT_FROM_OPTIONAL_DATASET,
    WORKFLOW_SIMPLE_CAT_TWICE,
    WORKFLOW_SIMPLE_MAPPING,
    WORKFLOW_WITH_INVALID_STATE,
    WORKFLOW_WITH_OLD_TOOL_VERSION,
    WORKFLOW_WITH_OUTPUT_COLLECTION,
    WORKFLOW_WITH_RULES_1,
    WORKFLOW_WITH_RULES_2,
)
from .framework import (
    retry_assertion_during_transitions,
    retry_during_transitions,
    RunsWorkflows,
    selenium_test,
    SeleniumTestCase,
)


class WorkflowEditorTestCase(SeleniumTestCase, RunsWorkflows):

    ensure_registered = True

    @selenium_test
    def test_basics(self):
        editor = self.components.workflow_editor
        annotation = "basic_test"
        name = self.workflow_create_new(annotation=annotation)
        self.assert_wf_name_is(name)
        self.assert_wf_annotation_is(annotation)

        editor.canvas_body.wait_for_visible()
        editor.tool_menu.wait_for_visible()

        # shouldn't have changes on fresh load
        save_button = self.components.workflow_editor.save_button
        save_button.wait_for_visible()
        assert save_button.has_class("disabled")

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
    def test_edit_annotation(self):
        editor = self.components.workflow_editor
        annotation = "new_annotation_test"
        name = self.workflow_create_new(annotation=annotation)
        edit_annotation = self.components.workflow_editor.edit_annotation
        self.assert_wf_annotation_is(annotation)

        editor.canvas_body.wait_for_visible()

        new_annotation = "look new annotation"
        edit_annotation.wait_for_and_send_keys(new_annotation)
        self.assert_workflow_has_changes_and_save()
        self.workflow_index_open_with_name(name)
        self.assert_wf_annotation_is(new_annotation)

    @selenium_test
    def test_edit_name(self):
        editor = self.components.workflow_editor
        name = self.workflow_create_new()
        editor.canvas_body.wait_for_visible()
        new_name = self._get_random_name()
        edit_name = self.components.workflow_editor.edit_name
        edit_name.wait_for_and_send_keys(new_name)

        self.assert_workflow_has_changes_and_save()
        self.workflow_index_open_with_name(new_name)
        self.assert_wf_name_is(name)

    @selenium_test
    def test_optional_select_data_field(self):
        editor = self.components.workflow_editor
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_SELECT_FROM_OPTIONAL_DATASET)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        editor = self.components.workflow_editor
        node = editor.node._(label="select_from_dataset_optional")
        node.title.wait_for_and_click()
        self.components.tool_form.parameter_checkbox(parameter="select_single").wait_for_and_click()
        # External (selenium-side) debounce hack for old backbone input
        # TODO: remove when form elements are all converted.
        self.components.tool_form.parameter_input(parameter="select_single").wait_for_and_send_keys("parameter valu")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.components.tool_form.parameter_input(parameter="select_single").wait_for_and_send_keys("e")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(workflow_id)
        tool_state = json.loads(workflow["steps"]["0"]["tool_state"])
        assert tool_state["select_single"] == "parameter value"
        # Disable optional button, resets value to null
        self.components.tool_form.parameter_checkbox(parameter="select_single").wait_for_and_click()
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(workflow_id)
        tool_state = json.loads(workflow["steps"]["0"]["tool_state"])
        assert tool_state["select_single"] is None
        # Enable button but don't provide a value
        self.components.tool_form.parameter_checkbox(parameter="select_single").wait_for_and_click()
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(workflow_id)
        tool_state = json.loads(workflow["steps"]["0"]["tool_state"])
        assert tool_state["select_single"] == ""

    @selenium_test
    def test_data_input(self):
        editor = self.components.workflow_editor

        name = self.workflow_create_new()
        self.workflow_editor_add_input(item_name="data_input")
        self.screenshot("workflow_editor_data_input_new")
        editor.label_input.wait_for_and_send_keys("input1")
        editor.annotation_input.wait_for_and_send_keys("my cool annotation")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_editor_data_input_filled_in")
        self.workflow_editor_click_save()

        self.workflow_index_open_with_name(name)
        data_input_node = editor.node._(label="input1")
        data_input_node.title.wait_for_and_click()
        label = editor.label_input.wait_for_value()
        assert label == "input1", label
        annotation = editor.annotation_input.wait_for_value()
        assert annotation == "my cool annotation", annotation
        data_input_node.destroy.wait_for_and_click()
        data_input_node.wait_for_absent()
        self.screenshot("workflow_editor_data_input_deleted")

    @selenium_test
    def test_collection_input(self):
        editor = self.components.workflow_editor

        name = self.workflow_create_new()
        self.workflow_editor_add_input(item_name="data_collection_input")
        self.screenshot("workflow_editor_data_collection_input_new")
        editor.label_input.wait_for_and_send_keys("input1")
        editor.annotation_input.wait_for_and_send_keys("my cool annotation")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_editor_data_collection_input_filled_in")
        self.workflow_editor_click_save()

        self.workflow_index_open_with_name(name)
        data_input_node = editor.node._(label="input1")
        data_input_node.title.wait_for_and_click()
        label = editor.label_input.wait_for_value()
        assert label == "input1", label
        annotation = editor.annotation_input.wait_for_value()
        assert annotation == "my cool annotation", annotation
        data_input_node.destroy.wait_for_and_click()
        data_input_node.wait_for_absent()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_editor_data_collection_input_deleted")

    @selenium_test
    def test_data_column_input_editing(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
steps:
  column_param_list:
    tool_id: column_param_list
    state:
      col: ["1","2","3"]
      col_names: ["a", "b", "c"]
      """
        )
        editor = self.components.workflow_editor
        node = editor.node._(label="column_param_list")
        node.title.wait_for_and_click()
        columns = self.components.tool_form.parameter_textarea(parameter="col")
        textarea_columns = columns.wait_for_visible()
        assert textarea_columns.get_attribute("value") == "1\n2\n3\n"
        column_names = self.components.tool_form.parameter_textarea(parameter="col_names")
        textarea_column_names = column_names.wait_for_visible()
        assert textarea_column_names.get_attribute("value") == "a\nb\nc\n"
        self.sleep_for(self.wait_types.UX_RENDER)
        self.set_text_element(columns, "4\n5\n6\n")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        self.driver.refresh()
        node.title.wait_for_and_click()
        textarea_columns = columns.wait_for_visible()
        assert textarea_columns.get_attribute("value") == "4\n5\n6\n"

    @selenium_test
    def test_integer_input(self):
        editor = self.components.workflow_editor

        name = self.workflow_create_new()
        self.workflow_editor_add_input(item_name="parameter_input")
        self.screenshot("workflow_editor_parameter_input_new")
        editor.label_input.wait_for_and_send_keys("input1")
        editor.annotation_input.wait_for_and_send_keys("my cool annotation")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_editor_parameter_input_filled_in")
        self.workflow_editor_click_save()

        self.workflow_index_open_with_name(name)
        data_input_node = editor.node._(label="input1")
        data_input_node.title.wait_for_and_click()
        label = editor.label_input.wait_for_value()
        assert label == "input1", label
        annotation = editor.annotation_input.wait_for_value()
        assert annotation == "my cool annotation", annotation
        data_input_node.destroy.wait_for_and_click()
        data_input_node.wait_for_absent()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_editor_parameter_input_deleted")

    @selenium_test
    def test_non_data_connections(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
inputs:
  input_int: integer
steps:
  simple_constructs:
    tool_id: simple_constructs
    label: tool_exec
    in:
      inttest: input_int
"""
        )
        self.screenshot("workflow_editor_parameter_connection_simple")
        self.assert_connected("input_int#output", "tool_exec#inttest")

        editor = self.components.workflow_editor

        tool_node = editor.node._(label="tool_exec")
        tool_input = tool_node.input_terminal(name="inttest")
        tool_input.wait_for_and_click()

        editor.connector_destroy_callout.wait_for_and_click()
        self.assert_not_connected("input_int#output", "tool_exec#inttest")
        self.screenshot("workflow_editor_parameter_connection_destroyed")

        # When connected, cannot turn it into a RuntimeValue..
        collapse_input = editor.collapse_icon(name="inttest")
        collapse_input.wait_for_absent_or_hidden()

        # If it is disconnected, then can specify as RuntimeValue
        connect_icon = editor.connect_icon(name="inttest")
        connect_icon.wait_for_visible()
        connect_icon.wait_for_and_click()
        collapse_input.wait_for_visible()

        # Also the connector should disappear
        tool_input.wait_for_absent_or_hidden()

        # Now make it connected again and watch the requests
        connect_icon.wait_for_and_click()

        tool_input.wait_for_visible()
        collapse_input.wait_for_absent_or_hidden()

        self.workflow_editor_connect(
            "input_int#output", "tool_exec#inttest", screenshot_partial="workflow_editor_parameter_connection_dragging"
        )
        self.assert_connected("input_int#output", "tool_exec#inttest")

    @selenium_test
    def test_non_data_map_over_carried_through(self):
        # Use auto_layout=false, which prevents placing any
        # step outside of the scroll area
        # xref: https://github.com/galaxyproject/galaxy/issues/13211
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
inputs:
  input_collection:
    type: collection
    collection_type: "list"
steps:
  param_value_from_file:
    tool_id: param_value_from_file
    in:
      input1: input_collection
  text_input_step:
    tool_id: param_text_option
    in:
      text_param: param_value_from_file/text_param
  collection_input:
    tool_id: identifier_collection
""",
            auto_layout=False,
        )
        self.workflow_editor_connect("text_input_step#out_file1", "collection_input#input1")
        self.assert_connected("text_input_step#out_file1", "collection_input#input1")

    def test_connecting_display_in_upload_false_connections(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
steps:
  step1:
    tool_id: test_sam_to_bam_conversions
  step2:
    tool_id: test_sam_to_bam_conversions
        """
        )

        self.workflow_editor_connect("step1#qname_input_sorted_bam_output", "step2#input5")
        self.assert_connected("step1#qname_input_sorted_bam_output", "step2#input5")

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

        self.workflow_editor_connect(
            "input1#output", "first_cat#input1", screenshot_partial="workflow_editor_connection_dragging"
        )
        self.assert_connected("input1#output", "first_cat#input1")

    @selenium_test
    def test_reconnecting_nodes(self):
        name = self.open_in_workflow_editor(WORKFLOW_SIMPLE_CAT_TWICE)
        self.assert_connected("input1#output", "first_cat#input1")
        self.workflow_editor_destroy_connection("first_cat#input1")
        self.assert_not_connected("input1#output", "first_cat#input1")
        self.workflow_editor_connect("input1#output", "first_cat#input1")
        self.assert_connected("input1#output", "first_cat#input1")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        self.workflow_index_open_with_name(name)
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
    def test_rendering_rules_workflow_1(self):
        self.open_in_workflow_editor(WORKFLOW_WITH_RULES_1)
        rule_output = "apply#output"
        random_lines_input = "random_lines#input"
        self.workflow_editor_maximize_center_pane()
        self.screenshot("workflow_editor_rules_1")
        self.assert_connected(rule_output, random_lines_input)
        self.assert_input_mapped(random_lines_input)
        self.workflow_editor_destroy_connection(random_lines_input)
        self.assert_not_connected(rule_output, random_lines_input)
        self.assert_input_not_mapped(random_lines_input)
        self.workflow_editor_connect(rule_output, random_lines_input)
        self.assert_connected(rule_output, random_lines_input)
        self.assert_input_mapped(random_lines_input)

    @selenium_test
    def test_rendering_rules_workflow_2(self):
        self.open_in_workflow_editor(WORKFLOW_WITH_RULES_2)
        self.workflow_editor_maximize_center_pane(collapse_right=False)

        editor = self.components.workflow_editor
        rule_builder = self.components.rule_builder

        rule_output = "apply#output"
        copy_list_input = "copy_list#input1"

        apply_node = editor.node._(label="apply")

        self.assert_connected(rule_output, copy_list_input)
        self.assert_input_mapped(copy_list_input)
        self.workflow_editor_destroy_connection(copy_list_input)
        self.assert_not_connected(rule_output, copy_list_input)
        self.assert_input_not_mapped(copy_list_input)
        self.workflow_editor_connect(rule_output, copy_list_input)
        self.assert_connected(rule_output, copy_list_input)
        self.assert_input_mapped(copy_list_input)

        apply_node.title.wait_for_and_click()
        self.screenshot("workflow_editor_rules_2_form")
        self.tool_parameter_edit_rules()
        rule_builder._.wait_for_visible()
        self.screenshot("workflow_editor_rules_2_builder")
        new_rules = dict(
            rules=[{"type": "add_column_metadata", "value": "identifier0"}],
            mapping=[{"type": "list_identifiers", "columns": [0]}],
        )
        self.rule_builder_set_source(json.dumps(new_rules))
        rule_builder.main_button_ok.wait_for_and_click()
        apply_node.title.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        # screenshot should have async warning about connection removed
        self.screenshot("workflow_editor_rules_2_after_change")
        self.assert_input_not_mapped(copy_list_input)
        # changing output collection type remove outbound connections, so this
        # this needs to be re-connected. Remove this re-connection if we upgrade
        # the workflow editor to try to re-establish the connection with different
        # mapping.
        self.workflow_editor_connect(rule_output, copy_list_input)
        self.assert_connected(rule_output, copy_list_input)
        # Regardless - this rules now say to connect a list to a list instead of a list
        # to a list:list, so there should be no mapping anymore even after connected.
        self.assert_input_not_mapped(copy_list_input)

    @selenium_test
    def test_save_as(self):
        name = self.workflow_upload_yaml_with_random_name(WORKFLOW_SIMPLE_CAT_TWICE)
        self.workflow_index_open()
        self.workflow_index_open_with_name(name)
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("workflow_editor_edit_menu")
        self.workflow_editor_click_option("Save As")

    @selenium_test
    def test_editor_tool_upgrade(self):
        workflow_populator = self.workflow_populator
        workflow_id = workflow_populator.upload_yaml_workflow(
            """class: GalaxyWorkflow
inputs: []
steps:
  - tool_id: multiple_versions
    tool_version: 0.1
    label: multiple_versions
    state:
      foo: bar
        """,
            exact_tools=True,
        )
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        editor = self.components.workflow_editor
        editor.node._(label="multiple_versions").wait_for_and_click()
        editor.tool_version_button.wait_for_and_click()
        assert self.select_dropdown_item("Switch to 0.2"), "Switch to tool version dropdown item not found"
        self.screenshot("workflow_editor_version_update")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(workflow_id)
        assert workflow["steps"]["0"]["tool_version"] == "0.2"

    @selenium_test
    def test_editor_tool_upgrade_message(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(WORKFLOW_WITH_OLD_TOOL_VERSION, exact_tools=True)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        self.assert_modal_has_text("Using version '0.2' instead of version '0.0.1'")
        self.screenshot("workflow_editor_tool_upgrade")
        self.components.workflow_editor.modal_button_continue.wait_for_and_click()
        self.assert_workflow_has_changes_and_save()

    @selenium_test
    def test_editor_subworkflow_tool_upgrade_message(self):
        workflow_populator = self.workflow_populator
        embedded_workflow = yaml.safe_load(WORKFLOW_WITH_OLD_TOOL_VERSION)
        # Create invalid tool state
        embedded_workflow["steps"]["mul_versions"]["state"]["inttest"] = "Invalid"
        outer_workflow = yaml.safe_load(
            """
class: GalaxyWorkflow
inputs:
  outer_input: data
steps:
  nested_workflow:
    run: {}
    in:
      input1: outer_input
        """
        )
        outer_workflow["steps"]["nested_workflow"]["run"] = embedded_workflow
        workflow_populator.upload_yaml_workflow(json.dumps(outer_workflow), exact_tools=True)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_modal_has_text("Using version '0.2' instead of version '0.0.1'")
        self.assert_modal_has_text("parameter 'inttest': an integer or workflow parameter is required")
        self.screenshot("workflow_editor_subworkflow_tool_upgrade")
        self.components.workflow_editor.modal_button_continue.wait_for_and_click()
        self.assert_workflow_has_changes_and_save()

    @staticmethod
    def set_text_element(element, value):
        # Try both, no harm here
        element.wait_for_and_send_keys(Keys.CONTROL, "a")
        element.wait_for_and_send_keys(Keys.COMMAND, "a")
        element.wait_for_and_send_keys(Keys.BACKSPACE)
        element.wait_for_and_send_keys(value)

    @selenium_test
    def test_editor_duplicate_node(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        editor = self.components.workflow_editor
        cat_node = editor.node._(label="first_cat")
        cat_node.wait_for_and_click()
        self.set_text_element(editor.label_input, "source label")
        # Select node using new label, ensures labels are synced between side panel and node
        cat_node = editor.node._(label="source label")
        self.assert_workflow_has_changes_and_save()
        editor.annotation_input.wait_for_and_send_keys("source annotation")
        self.assert_workflow_has_changes_and_save()
        editor.configure_output(output="out_file1").wait_for_and_click()
        output_label = editor.label_output(output="out_file1")
        self.set_text_element(output_label, "workflow output label")
        self.set_text_element(editor.rename_output, "renamed_output")
        editor.change_datatype.wait_for_and_click()
        editor.select_dataype_text_search.wait_for_and_send_keys("bam")
        editor.select_datatype(datatype="bam").wait_for_and_click()
        self.set_text_element(editor.add_tags, "#crazynewtag")
        self.set_text_element(editor.remove_tags, "#oldboringtag")
        self.sleep_for(self.wait_types.UX_RENDER)
        cat_node.clone.wait_for_and_click()
        editor.label_input.wait_for_and_send_keys("cloned label")
        output_label = editor.label_output(output="out_file1")
        self.set_text_element(output_label, "cloned output label")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        edited_workflow = self.workflow_populator.download_workflow(workflow_id)
        source_step = next(iter(step for step in edited_workflow["steps"].values() if step["label"] == "source label"))
        cloned_step = next(iter(step for step in edited_workflow["steps"].values() if step["label"] == "cloned label"))
        assert source_step["annotation"] == cloned_step["annotation"] == "source annotation"
        assert source_step["workflow_outputs"][0]["label"] == "workflow output label"
        assert cloned_step["workflow_outputs"][0]["label"] == "cloned output label"
        assert len(source_step["post_job_actions"]) == len(cloned_step["post_job_actions"]) == 4
        assert source_step["post_job_actions"] == cloned_step["post_job_actions"]

    @selenium_test
    def test_editor_embed_workflow(self):
        workflow_populator = self.workflow_populator
        child_workflow_name = self._get_random_name()
        workflow_populator.upload_yaml_workflow(WORKFLOW_OPTIONAL_TRUE_INPUT_COLLECTION, name=child_workflow_name)
        parent_workflow_id = workflow_populator.upload_yaml_workflow(
            """class: GalaxyWorkflow
inputs: []
steps:
  - tool_id: multiple_versions
    tool_version: 0.1
    label: multiple_versions
    state:
      foo: bar
        """
        )
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        editor = self.components.workflow_editor
        editor.canvas_body.wait_for_visible()
        editor.tool_menu.wait_for_visible()
        editor.tool_menu_section_link(section_name="workflows").wait_for_and_click()
        editor.workflow_link(workflow_title=child_workflow_name).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(parent_workflow_id)
        subworkflow_step = workflow["steps"]["1"]
        assert subworkflow_step["name"] == child_workflow_name
        assert subworkflow_step["type"] == "subworkflow"
        assert subworkflow_step["subworkflow"]["a_galaxy_workflow"] == "true"

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
        workflow_populator.upload_yaml_workflow(
            """
class: GalaxyWorkflow
inputs:
  - id: input1
steps:
  - tool_id: missing
    label: first_cat
    state:
      foo: bar
"""
        )
        self.workflow_index_open()
        self.workflow_index_click_option("Edit")
        self.assert_modal_has_text("Tool is not installed")
        self.screenshot("workflow_editor_missing_tool")

    @selenium_test
    def test_workflow_bookmarking(self):
        @retry_during_transitions
        def assert_workflow_bookmarked_status(target_status):
            name_matches = [c.text == new_workflow_name for c in self.components.tool_panel.workflow_names.all()]
            status = any(name_matches)
            self.assertTrue(status == target_status)

        new_workflow_name = self.workflow_create_new(clear_placeholder=True)

        # Assert workflow not initially bookmarked.
        assert_workflow_bookmarked_status(False)

        self.components.workflow_editor.canvas_body.wait_for_visible()
        self.wait_for_selector_absent_or_hidden(self.modal_body_selector())
        self.components.masthead.workflow.wait_for_and_click()

        # parse workflow table
        table_elements = self.workflow_index_table_elements()
        self.sleep_for(self.wait_types.UX_RENDER)
        bookmark_td = table_elements[0].find_elements_by_tag_name("td")[4]

        # get bookmark pseudo element
        # https://stackoverflow.com/questions/45427223/click-on-pseudo-element-using-selenium
        self.action_chains().move_to_element_with_offset(bookmark_td, 20, 20).click().perform()
        self.sleep_for(self.wait_types.UX_TRANSITION)

        # search for bookmark in tools menu
        self.components.tool_panel.search.wait_for_and_send_keys(new_workflow_name)
        assert_workflow_bookmarked_status(True)

    def workflow_editor_maximize_center_pane(self, collapse_left=True, collapse_right=True):
        if collapse_left:
            self.components._.left_panel_collapse.wait_for_and_click()
        if collapse_right:
            self.components._.right_panel_collapse.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    def workflow_editor_connect(self, source, sink, screenshot_partial=None):
        source_id, sink_id = self.workflow_editor_source_sink_terminal_ids(source, sink)
        source_element = self.driver.find_element_by_css_selector(f"#{source_id}")
        sink_element = self.driver.find_element_by_css_selector(f"#{sink_id}")

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

    def open_in_workflow_editor(self, yaml_content, auto_layout=True):
        name = self.workflow_upload_yaml_with_random_name(yaml_content)
        self.workflow_index_open()
        self.workflow_index_open_with_name(name)
        if auto_layout:
            self.workflow_editor_click_option("Auto Layout")
        return name

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

    def workflow_editor_add_input(self, item_name="data_input"):
        editor = self.components.workflow_editor

        # Make sure we're on the the workflow editor and not clicking the main tool panel.
        editor.canvas_body.wait_for_visible()

        editor.tool_menu.wait_for_visible()
        editor.tool_menu_section_link(section_name="inputs").wait_for_and_click()
        editor.tool_menu_item_link(item_name=item_name).wait_for_and_click()

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

    @retry_assertion_during_transitions
    def assert_wf_name_is(self, expected_name):
        edit_name_element = self.components.workflow_editor.edit_name.wait_for_visible()
        actual_name = edit_name_element.get_attribute("value")
        assert expected_name in actual_name, f"'{expected_name}' unequal name '{actual_name}'"

    @retry_assertion_during_transitions
    def assert_wf_annotation_is(self, expected_annotation):
        edit_annotation = self.components.workflow_editor.edit_annotation
        edit_annotation_element = edit_annotation.wait_for_visible()
        actual_annotation = edit_annotation_element.get_attribute("value")
        assert (
            expected_annotation in actual_annotation
        ), f"'{expected_annotation}' unequal annotation '{actual_annotation}'"

    @retry_assertion_during_transitions
    def assert_modal_has_text(self, expected_text):
        modal_element = self.components.workflow_editor.state_modal_body.wait_for_visible()
        text = modal_element.text
        assert expected_text in text, f"Failed to find expected text [{expected_text}] in modal text [{text}]"

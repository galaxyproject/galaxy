import json
from typing import Optional

import pytest
import yaml
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from seletools.actions import drag_and_drop

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


class TestWorkflowEditor(SeleniumTestCase, RunsWorkflows):
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

        self.hover_over(self.components._.left_panel_drag.wait_for_visible())
        self.components._.left_panel_collapse.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)

        self.screenshot("workflow_editor_left_collapsed")

        self.hover_over(self.components._.right_panel_drag.wait_for_visible())
        self.components._.right_panel_collapse.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)

        self.screenshot("workflow_editor_left_and_right_collapsed")

    @selenium_test
    def test_edit_annotation(self):
        editor = self.components.workflow_editor
        annotation = "new_annotation_test"
        name = self.create_and_wait_for_new_workflow_in_editor(annotation=annotation)
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
        name = self.create_and_wait_for_new_workflow_in_editor()
        new_name = self._get_random_name()
        edit_name = self.components.workflow_editor.edit_name
        edit_name.wait_for_and_send_keys(new_name)

        self.assert_workflow_has_changes_and_save()
        self.workflow_index_open_with_name(new_name)
        self.assert_wf_name_is(name)

    @selenium_test
    def test_edit_license(self):
        editor = self.components.workflow_editor
        name = self.create_and_wait_for_new_workflow_in_editor()
        editor.license_selector.wait_for_visible()
        assert "Do not specify" in editor.license_current_value.wait_for_text()

        self.workflow_editor_set_license("MIT")
        self.workflow_editor_click_save()

        self.workflow_index_open_with_name(name)
        editor.license_selector.wait_for_visible()
        assert "MIT" in editor.license_current_value.wait_for_text()

    @selenium_test
    def test_parameter_regex_validation(self):
        editor = self.components.workflow_editor
        workflow_run = self.components.workflow_run

        parameter_name = "text_param"
        name = self.create_and_wait_for_new_workflow_in_editor()
        self.workflow_editor_add_parameter_input()
        editor.label_input.wait_for_and_send_keys(parameter_name)
        # this really should be parameterized with the repeat name
        self.components.tool_form.repeat_insert.wait_for_and_click()
        self.components.tool_form.parameter_input(
            parameter="parameter_definition|validators_0|regex_match"
        ).wait_for_and_send_keys("moocow.*")
        self.components.tool_form.parameter_input(
            parameter="parameter_definition|validators_0|regex_doc"
        ).wait_for_and_send_keys("input must start with moocow")
        self.save_after_node_form_changes()

        self.workflow_run_with_name(name)
        self.sleep_for(self.wait_types.UX_TRANSITION)
        input_element = workflow_run.simplified_input(label=parameter_name).wait_for_and_click()
        input_element.send_keys("startswrong")
        workflow_run.run_workflow_disabled.wait_for_absent()
        workflow_run.run_error.assert_absent_or_hidden()
        self.workflow_run_submit()
        element = workflow_run.run_error.wait_for_present()
        assert "input must start with moocow" in element.text

    @selenium_test
    def test_int_parameter_minimum_validation(self):
        editor = self.components.workflow_editor
        workflow_run = self.components.workflow_run

        parameter_name = "int_param"
        name = self.create_and_wait_for_new_workflow_in_editor()
        self.workflow_editor_add_parameter_input()
        editor.label_input.wait_for_and_send_keys(parameter_name)
        select_field = self.components.tool_form.parameter_select(parameter="parameter_definition|parameter_type")
        self.select_set_value(select_field, "integer")
        self.components.tool_form.parameter_input(parameter="parameter_definition|min").wait_for_and_send_keys("4")
        self.save_after_node_form_changes()

        self.workflow_run_with_name(name)
        self.sleep_for(self.wait_types.UX_TRANSITION)
        input_element = workflow_run.simplified_input(label=parameter_name).wait_for_and_click()
        input_element.send_keys("3")
        workflow_run.run_workflow_disabled.wait_for_absent()
        workflow_run.run_error.assert_absent_or_hidden()
        self.workflow_run_submit()
        element = workflow_run.run_error.wait_for_present()
        # follow up with a bigger PR to just make this (4 <= value) right? need to set default message
        # in parameter validators
        assert "Value ('3') must fulfill (4 <= value <= +infinity)" in element.text, element.text

    @selenium_test
    def test_float_parameter_maximum_validation(self):
        editor = self.components.workflow_editor
        workflow_run = self.components.workflow_run

        parameter_name = "float_param"
        name = self.create_and_wait_for_new_workflow_in_editor()
        self.workflow_editor_add_parameter_input()
        editor.label_input.wait_for_and_send_keys(parameter_name)
        select_field = self.components.tool_form.parameter_select(parameter="parameter_definition|parameter_type")
        self.select_set_value(select_field, "float")
        self.components.tool_form.parameter_input(parameter="parameter_definition|max").wait_for_and_send_keys("3.14")
        self.save_after_node_form_changes()

        self.workflow_run_with_name(name)
        self.sleep_for(self.wait_types.UX_TRANSITION)
        input_element = workflow_run.simplified_input(label=parameter_name).wait_for_and_click()
        input_element.send_keys("3.2")
        workflow_run.run_workflow_disabled.wait_for_absent()
        workflow_run.run_error.assert_absent_or_hidden()
        self.workflow_run_submit()
        element = workflow_run.run_error.wait_for_present()
        # see message in test test_int_parameter_minimum_validation about making this a little more human
        # friendly.
        assert "Value ('3.2') must fulfill (-infinity <= value <= 3.14)" in element.text, element.text

    @selenium_test
    def test_optional_select_data_field(self):
        editor = self.components.workflow_editor
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_SELECT_FROM_OPTIONAL_DATASET)
        self.workflow_index_open()
        self.components.workflows.edit_button.wait_for_and_click()
        editor = self.components.workflow_editor
        node = editor.node._(label="select_from_dataset_optional")
        node.title.wait_for_and_click()
        self.components.tool_form.parameter_checkbox(parameter="select_single").wait_for_and_click()
        self.components.tool_form.parameter_input(parameter="select_single").wait_for_and_send_keys("parameter value")
        self.save_after_node_form_changes()
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

        name = self.workflow_create_new(save_workflow=False)
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
  cat1:
    # regression test, ensures connecting works in the presence of data input terminals
    tool_id: cat1
"""
        )
        self.screenshot("workflow_editor_parameter_connection_simple")
        self.assert_connected("input_int#output", "tool_exec#inttest")

        editor = self.components.workflow_editor

        tool_node = editor.node._(label="tool_exec")
        tool_input = tool_node.input_terminal(name="inttest")
        self.hover_over(tool_input.wait_for_visible())
        tool_node.connector_destroy_callout(name="inttest").wait_for_and_click()
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
        self.hover_over(cat_input.wait_for_visible())
        cat_node.connector_destroy_callout(name="input1").wait_for_visible()
        self.screenshot("workflow_editor_connection_callout")
        cat_node.connector_destroy_callout(name="input1").wait_for_and_click()
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
        self.components.workflows.edit_button.wait_for_and_click()
        editor = self.components.workflow_editor
        editor.node._(label="multiple_versions").wait_for_and_click()
        editor.tool_version_button.wait_for_and_click()
        assert self.select_dropdown_item("Switch to 0.2"), "Switch to tool version dropdown item not found"
        self.screenshot("workflow_editor_version_update")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(workflow_id)
        assert workflow["steps"]["0"]["tool_version"] == "0.2"
        editor.node._(label="multiple_versions").wait_for_and_click()
        editor.tool_version_button.wait_for_and_click()
        assert self.select_dropdown_item("Switch to 0.1+galaxy6"), "Switch to tool version dropdown item not found"
        self.screenshot("workflow_editor_version_downgrade")
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(workflow_id)
        assert workflow["steps"]["0"]["tool_version"] == "0.1+galaxy6"

    @selenium_test
    def test_editor_tool_upgrade_message(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(WORKFLOW_WITH_OLD_TOOL_VERSION, exact_tools=True)
        self.workflow_index_open()
        self.components.workflows.edit_button.wait_for_and_click()
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
        self.components.workflows.edit_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_modal_has_text("Using version '0.2' instead of version '0.0.1'")
        self.assert_modal_has_text("Parameter 'inttest': an integer or workflow parameter is required")
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
    def test_change_datatype(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
inputs: []
steps:
  - tool_id: create_2
    label: create_2
  - tool_id: checksum
    label: checksum
    in:
      input: create_2/out_file1
"""
        )
        editor = self.components.workflow_editor
        self.assert_connected("create_2#out_file1", "checksum#input")
        node = editor.node._(label="create_2")
        node.wait_for_and_click()
        editor.configure_output(output="out_file1").wait_for_and_click()
        editor.change_datatype.wait_for_and_click()
        editor.select_datatype_text_search.wait_for_and_send_keys("bam")
        editor.select_datatype(datatype="bam").wait_for_and_click()
        editor.node.output_data_row(output_name="out_file1", extension="bam").wait_for_visible()
        self.assert_connection_invalid("create_2#out_file1", "checksum#input")
        # Assert save button
        save_button = self.components.workflow_editor.save_button
        save_button.wait_for_and_click()
        # Will trigger confirmation modal
        self.components.workflow_editor.save_workflow_confirmation_button.wait_for_and_click()
        # Make connection valid again
        editor.change_datatype.wait_for_and_click()
        editor.select_datatype_text_search.wait_for_and_send_keys("tabular")
        editor.select_datatype(datatype="tabular").wait_for_and_click()
        # Assert connection is valid
        self.assert_connected("create_2#out_file1", "checksum#input")

    @selenium_test
    def test_change_datatype_post_job_action_lost_regression(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
inputs: []
steps:
  - tool_id: create_2
    label: create_2
    outputs:
      out_file1:
        change_datatype: bam
  - tool_id: metadata_bam
    label: metadata_bam
    in:
      input_bam: create_2/out_file1
"""
        )
        self.assert_connected("create_2#out_file1", "metadata_bam#input_bam")
        editor = self.components.workflow_editor
        node = editor.node._(label="create_2")
        node.wait_for_and_click()
        self.assert_connected("create_2#out_file1", "metadata_bam#input_bam")

    @selenium_test
    def test_change_datatype_in_subworkflow(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
inputs: []
steps:
  nested_workflow:
    run:
        class: GalaxyWorkflow
        inputs: []
        steps:
          - tool_id: create_2
            label: create_2
            outputs:
              out_file1:
                change_datatype: bam
        outputs:
          workflow_output:
            outputSource: create_2/out_file1
  metadata_bam:
    tool_id: metadata_bam
"""
        )
        editor = self.components.workflow_editor
        node = editor.node._(label="nested_workflow")
        node.wait_for_and_click()
        node.output_data_row(output_name="workflow_output", extension="bam").wait_for_visible()
        # Move canvas, so terminals are in viewport
        self.move_center_of_canvas(xoffset=100, yoffset=100)
        self.workflow_editor_connect("nested_workflow#workflow_output", "metadata_bam#input_bam")
        self.assert_connected("nested_workflow#workflow_output", "metadata_bam#input_bam")

    @pytest.mark.xfail
    @selenium_test
    def test_edit_subworkflow(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
inputs: []
steps:
  nested_workflow:
    run:
        class: GalaxyWorkflow
        inputs: []
        steps:
          - tool_id: create_2
            label: create_2
"""
        )
        editor = self.components.workflow_editor
        node = editor.node._(label="nested_workflow")
        node.wait_for_and_click()
        editor.edit_subworkflow.wait_for_and_click()
        node = editor.node._(label="create_2")
        node.wait_for_and_click()

    @selenium_test
    def test_editor_duplicate_node(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.workflow_index_open()
        self.components.workflows.edit_button.wait_for_and_click()
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
        editor.select_datatype_text_search.wait_for_and_send_keys("bam")
        editor.select_datatype(datatype="bam").wait_for_and_click()
        editor.add_tags_button.wait_for_and_click()
        editor.add_tags_input.wait_for_and_send_keys("#crazynewtag" + Keys.ENTER + Keys.ESCAPE)
        editor.remove_tags_button.wait_for_and_click()
        editor.remove_tags_input.wait_for_and_send_keys("#oldboringtag" + Keys.ENTER + Keys.ESCAPE)
        self.sleep_for(self.wait_types.UX_RENDER)
        cat_node.clone.wait_for_and_click()
        editor.label_input.wait_for_and_send_keys(Keys.BACKSPACE * 20)
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
        self.setup_subworkflow()

    def setup_subworkflow(self):
        workflow_populator = self.workflow_populator
        child_workflow_name = self._get_random_name()
        workflow_populator.upload_yaml_workflow(WORKFLOW_OPTIONAL_TRUE_INPUT_COLLECTION, name=child_workflow_name)
        parent_workflow_id = workflow_populator.upload_yaml_workflow(
            """class: GalaxyWorkflow
inputs:
  input_collection:
    type: collection
    collection_type: "list"
steps:
  - tool_id: multiple_versions
    tool_version: 0.1
    label: multiple_versions
    state:
      foo: bar
        """
        )
        self.workflow_index_open()
        self.components.workflows.edit_button.wait_for_and_click()
        editor = self.components.workflow_editor
        editor.canvas_body.wait_for_visible()
        editor.tool_menu.wait_for_visible()
        editor.tool_menu_section_link(section_name="workflows").wait_for_and_click()
        editor.workflow_link(workflow_title=child_workflow_name).wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(parent_workflow_id)
        subworkflow_step = workflow["steps"]["2"]
        assert subworkflow_step["name"] == child_workflow_name
        assert subworkflow_step["type"] == "subworkflow"
        assert subworkflow_step["subworkflow"]["a_galaxy_workflow"] == "true"
        self.workflow_editor_connect("input_collection#output", f"{child_workflow_name}#input1")
        self.assert_connected("input_collection#output", f"{child_workflow_name}#input1")
        self.assert_workflow_has_changes_and_save()
        workflow = self.workflow_populator.download_workflow(parent_workflow_id)
        subworkflow_step = workflow["steps"]["2"]
        assert subworkflow_step["input_connections"]["input1"]["input_subworkflow_step_id"] == 0
        return child_workflow_name

    @selenium_test
    def test_editor_insert_steps(self):
        steps_to_insert = self.workflow_upload_yaml_with_random_name(WORKFLOW_SIMPLE_CAT_TWICE)
        annotation = "insert step test"
        self.workflow_create_new(annotation=annotation)
        self.workflow_editor_add_input(item_name="data_input")
        editor = self.components.workflow_editor
        editor.canvas_body.wait_for_visible()
        editor.tool_menu.wait_for_visible()
        editor.tool_menu_section_link(section_name="workflows").wait_for_and_click()
        editor.insert_steps(workflow_title=steps_to_insert).wait_for_and_click()
        self.assert_connected("input1#output", "first_cat#input1")
        self.assert_workflow_has_changes_and_save()
        workflow_id = self.driver.current_url.split("id=")[1]
        workflow = self.workflow_populator.download_workflow(workflow_id)
        assert len(workflow["steps"]) == 3

    @selenium_test
    def test_editor_create_conditional_step(self):
        editor = self.components.workflow_editor
        self.workflow_create_new(annotation="simple when step definition")
        # Insert a boolean parameter
        self.workflow_editor_add_input(item_name="parameter_input")
        param_type_element = editor.param_type_form.wait_for_present()
        self.switch_param_type(param_type_element, "Boolean")
        editor.label_input.wait_for_and_send_keys("param_input")
        editor.tool_menu.wait_for_visible()
        # Insert cat tool
        self.tool_open("cat")
        self.sleep_for(self.wait_types.UX_RENDER)
        editor.label_input.wait_for_and_send_keys("downstream_step")
        # Insert head tool
        self.tool_open("head")
        self.workflow_editor_click_option("Auto Layout")
        self.sleep_for(self.wait_types.UX_RENDER)
        editor.label_input.wait_for_and_send_keys("conditional_step")
        # Connect head to cat
        self.workflow_editor_connect("conditional_step#out_file1", "downstream_step#input1")
        self.assert_connected("conditional_step#out_file1", "downstream_step#input1")
        # Make head tool conditional
        conditional_node = editor.node._(label="conditional_step")
        conditional_node.input_terminal(name="input").wait_for_present()
        # Assert no when input before making step conditional
        conditional_node.input_terminal(name="when").wait_for_absent()
        conditional_toggle = editor.step_when.wait_for_present()
        self.action_chains().move_to_element(conditional_toggle).click().perform()
        # Toggling conditional should cause when input to appear
        conditional_node.input_terminal(name="when").wait_for_present()
        self.action_chains().move_to_element(conditional_toggle).click().perform()
        # Toggling conditional should cause when input to disappear
        conditional_node.input_terminal(name="when").wait_for_absent()
        self.action_chains().move_to_element(conditional_toggle).click().perform()
        conditional_node.input_terminal(name="when").wait_for_present()
        # Output connection should be invalid, as output from conditional step is potentially null
        self.assert_connection_invalid("conditional_step#out_file1", "downstream_step#input1")
        downstream_step = editor.node._(label="downstream_step")
        downstream_step.destroy.wait_for_and_click()
        downstream_step.wait_for_absent()
        # Connect boolean input to when
        self.workflow_editor_connect("param_input#output", "conditional_step#when")
        self.assert_connected("param_input#output", "conditional_step#when")
        # Change boolean input parameter to invalid parameter type
        editor.node._(label="param_input").wait_for_and_click()
        param_type_element = editor.param_type_form.wait_for_present()
        self.switch_param_type(param_type_element, "Text")
        self.assert_connection_invalid("param_input#output", "conditional_step#when")
        self.workflow_editor_destroy_connection("conditional_step#when")
        # Make sure the when input is still shown
        conditional_node.input_terminal(name="when").wait_for_present()
        # Assert save button is disabled because of disconnected when
        save_button = self.components.workflow_editor.save_button
        save_button.wait_for_visible()
        # TODO: hook up best practice panel, disable save when "when" not connected
        # assert save_button.has_class("disabled")

    def test_conditional_subworkflow_step(self):
        child_workflow_name = self.setup_subworkflow()
        editor = self.components.workflow_editor
        # Insert a boolean parameter
        self.workflow_editor_add_input(item_name="parameter_input")
        param_type_element = editor.param_type_form.wait_for_present()
        self.switch_param_type(param_type_element, "Boolean")
        editor.label_input.wait_for_and_send_keys("param_input")
        self.workflow_editor_click_option("Auto Layout")
        self.sleep_for(self.wait_types.UX_RENDER)
        conditional_node = editor.node._(label=child_workflow_name)
        conditional_node.wait_for_and_click()
        conditional_toggle = editor.step_when.wait_for_present()
        self.action_chains().move_to_element(conditional_toggle).click().perform()
        conditional_node.input_terminal(name="when").wait_for_present()
        self.workflow_editor_connect("param_input#output", f"{child_workflow_name}#when")
        self.assert_connected("param_input#output", f"{child_workflow_name}#when")
        self.assert_workflow_has_changes_and_save()

    def switch_param_type(self, element, param_type):
        self.action_chains().move_to_element(element).click().send_keys(param_type).send_keys(Keys.ENTER).perform()

    @selenium_test
    def test_editor_invalid_tool_state(self):
        workflow_populator = self.workflow_populator
        workflow_populator.upload_yaml_workflow(WORKFLOW_WITH_INVALID_STATE, exact_tools=True)
        self.workflow_index_open()
        self.components.workflows.edit_button.wait_for_and_click()
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
        self.components.workflows.edit_button.wait_for_and_click()
        self.assert_modal_has_text("Tool is not installed")
        self.screenshot("workflow_editor_missing_tool")

    @selenium_test
    def test_workflow_bookmarking(self):
        @retry_during_transitions
        def assert_workflow_bookmarked_status(target_status):
            name_matches = [c.text == new_workflow_name for c in self.components.tool_panel.workflow_names.all()]
            status = any(name_matches)
            assert status == target_status

        new_workflow_name = self.workflow_create_new(clear_placeholder=True)
        self.components.workflow_editor.canvas_body.wait_for_visible()
        self.wait_for_selector_absent_or_hidden(self.modal_body_selector())

        # Assert workflow not initially bookmarked.
        self.navigate_to_tools()
        assert_workflow_bookmarked_status(False)

        self.click_activity_workflow()
        self.components.workflows.bookmark_link(action="add").wait_for_and_click()

        # search for bookmark in tools menu
        self.navigate_to_tools()
        assert_workflow_bookmarked_status(True)

    def tab_to(self, accessible_name, direction="forward"):
        for _ in range(100):
            ac = self.action_chains()
            if direction == "backwards":
                ac.key_down(Keys.SHIFT)
            ac.send_keys(Keys.TAB)
            if direction == "backwards":
                ac.key_down(Keys.SHIFT)
            ac.perform()
            if accessible_name in self.driver.switch_to.active_element.accessible_name:
                return self.driver.switch_to.active_element
        else:
            raise Exception(f"Could not tab to element containing '{accessible_name}' in aria-label")

    @selenium_test
    def test_aria_connections_menu(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    position:
      # Step should be positioned off-screen, tabbing should scroll to node
      top: 2000
      left: 2000
    tool_id: cat
    in:
      input1: input1
      queries_0|input2: input1
""",
            auto_layout=False,
        )
        self.assert_connected("input1#output", "first_cat#input1")
        self.screenshot("workflow_editor_connection_simple")
        self.components.workflow_editor.canvas_body.wait_for_and_click()
        output_connector = self.tab_to("Press space to see a list of available inputs")
        output_connector.send_keys(Keys.SPACE)
        assert self.driver.switch_to.active_element.text == "Disconnect from input1 in step 2: first_cat"
        self.driver.switch_to.active_element.send_keys(Keys.ENTER)
        self.assert_not_connected("input1#output", "first_cat#input1")
        self.action_chains().move_to_element(self.components.workflow_editor.canvas_body.wait_for_and_click()).perform()
        output_connector = self.tab_to("Press space to see a list of available inputs")
        output_connector.send_keys(Keys.SPACE)
        assert self.driver.switch_to.active_element.text == "Connect to input1 in step 2: first_cat"
        self.driver.switch_to.active_element.send_keys(Keys.ENTER)
        self.assert_connected("input1#output", "first_cat#input1")
        self.action_chains().move_to_element(self.components.workflow_editor.canvas_body.wait_for_and_click()).perform()
        output_connector = self.tab_to("Press space to see a list of available inputs")
        output_connector = self.tab_to("Press space to see a list of available inputs")
        output_connector.send_keys(Keys.SPACE)
        assert self.driver.switch_to.active_element.text == "No compatible input found in workflow"

    @selenium_test
    def test_insert_input_handling(self):
        self.open_in_workflow_editor(
            """class: GalaxyWorkflow
inputs: []
steps:
  build_list:
    tool_id: __BUILD_LIST__
        """
        )
        editor = self.components.workflow_editor
        node = editor.node._(label="build_list")
        node.wait_for_and_click()
        assert not node.has_class("input-terminal")
        self.components.tool_form.repeat_insert.wait_for_and_click()
        node.input_terminal(name="datasets_0|input").wait_for_present()
        self.components.tool_form.repeat_insert.wait_for_and_click()
        node.input_terminal(name="datasets_1|input").wait_for_present()
        self.assert_workflow_has_changes_and_save()

    @selenium_test
    def test_workflow_output_handling(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
inputs: []
outputs:
  first_out:
    outputSource: first/out_file1
  second_out:
    outputSource: second/out_file1
steps:
  first:
    tool_id: create_2
  second:
    tool_id: create_2
""",
            auto_layout=True,
        )
        editor = self.components.workflow_editor
        # assert both steps have one workflow output each
        first = editor.node._(label="first")
        first.workflow_output_toggle_active(name="out_file1").wait_for_visible()
        first.workflow_output_toggle_active(name="out_file2").wait_for_absent()
        second = editor.node._(label="second")
        second.workflow_output_toggle_active(name="out_file1").wait_for_visible()
        second.workflow_output_toggle_active(name="out_file2").wait_for_absent()
        # toggle out_file1 on second step, both outputs not active
        second.workflow_output_toggle(name="out_file1").wait_for_and_click()
        # just toggling outputs doesn't set a label
        second.workflow_output_toggle_active(name="out_file1").wait_for_absent()
        second.workflow_output_toggle_active(name="out_file2").wait_for_absent()
        # switch to first node
        editor.node._(label="first").wait_for_and_click()
        # toggle out_file1 on first step
        first.workflow_output_toggle(name="out_file1").wait_for_and_click()
        first.workflow_output_toggle_active(name="out_file1").wait_for_absent()
        # turn out_file1 back on
        first.workflow_output_toggle(name="out_file1").wait_for_and_click()
        first.workflow_output_toggle_active(name="out_file1").wait_for_visible()
        # turn out_file1 off
        first.workflow_output_toggle(name="out_file1").wait_for_and_click()
        first.workflow_output_toggle_active(name="out_file1").wait_for_absent()
        editor.node._(label="second").wait_for_and_click()
        editor.node._(label="first").wait_for_and_click()
        # make sure workflow outputs are both off for second step
        first.workflow_output_toggle_active(name="out_file1").wait_for_absent()
        first.workflow_output_toggle_active(name="out_file2").wait_for_absent()
        # add an output label
        editor.configure_output(output="out_file1").wait_for_and_click()
        output_label = editor.label_output(output="out_file1")
        self.set_text_element(output_label, "workflow output label")
        # should indicate active workflow output
        first.workflow_output_toggle_active(name="out_file1").wait_for_visible()
        self.set_text_element(output_label, "")
        # deleting label also deletes active output
        first.workflow_output_toggle_active(name="out_file1").wait_for_absent()
        # set duplicate label
        output_label = editor.label_output(output="out_file1")
        self.set_text_element(output_label, "workflow output label")
        editor.node._(label="second").wait_for_and_click()
        editor.configure_output(output="out_file1").wait_for_and_click()
        output_label = editor.label_output(output="out_file1")
        self.set_text_element(output_label, "workflow output label")
        # should show error
        editor.duplicate_label_error(output="out_file1").wait_for_visible()
        # make label unique
        self.set_text_element(output_label, "workflow output label2")
        # should not show error
        editor.duplicate_label_error(output="out_file1").wait_for_absent()

    @selenium_test
    def test_map_over_output_indicator(self):
        self.open_in_workflow_editor(
            """
class: GalaxyWorkflow
inputs:
  list:
    type: collection
    collection_type: "list"
  nested_list:
    type: collection
    collection_type: "list:list"
steps:
  filter:
    tool_id: __FILTER_FROM_FILE__
"""
        )
        self.assert_node_output_is("filter#output_filtered", "any")
        self.workflow_editor_connect("list#output", "filter#input")
        self.assert_node_output_is("filter#output_filtered", "list")
        self.workflow_editor_connect("nested_list#output", "filter#how|filter_source")
        self.assert_node_output_is("filter#output_filtered", "list", "list:list:list")
        self.workflow_editor_destroy_connection("filter#how|filter_source")
        self.assert_node_output_is("filter#output_filtered", "list")

    @selenium_test
    def test_editor_place_comments(self):
        editor = self.components.workflow_editor

        self.workflow_create_new(annotation="simple workflow")
        self.sleep_for(self.wait_types.UX_RENDER)

        canvas = editor.canvas_body.wait_for_visible()

        # select text comment tool use all options and set font size to 2
        editor.tool_bar.tool(tool="text_comment").wait_for_and_click()
        editor.tool_bar.toggle_bold.wait_for_and_click()
        editor.tool_bar.toggle_italic.wait_for_and_click()
        editor.tool_bar.color(color="pink").wait_for_and_click()
        editor.tool_bar.font_size.wait_for_and_click()
        self.action_chains().send_keys(Keys.LEFT * 5).send_keys(Keys.RIGHT).perform()

        # place text comment
        self.mouse_drag(from_element=canvas, from_offset=(-200, -200), to_offset=(400, 110))

        self.action_chains().send_keys("Hello World").perform()

        # check if all options were applied
        comment_content: WebElement = editor.comment.text_inner.wait_for_visible()
        assert comment_content.text == "Hello World"
        comment_content_class = comment_content.get_attribute("class")
        assert comment_content_class
        assert "bold" in comment_content_class
        assert "italic" in comment_content_class

        # check for correct size
        width, height = self.get_element_size(editor.comment._.wait_for_visible())

        assert width == 400
        assert height == 110

        editor.comment.text_comment.wait_for_and_click()
        editor.comment.delete.wait_for_and_click()
        editor.comment.text_comment.wait_for_absent()

        # place and test markdown comment
        editor.tool_bar.tool(tool="markdown_comment").wait_for_and_click()
        editor.tool_bar.color(color="lime").wait_for_and_click()
        self.mouse_drag(from_element=canvas, from_offset=(-100, -100), to_offset=(200, 220))
        self.action_chains().send_keys("# Hello World").perform()

        editor.tool_bar.tool(tool="pointer").wait_for_and_click()

        markdown_comment_content: WebElement = editor.comment.markdown_rendered.wait_for_visible()
        assert markdown_comment_content.text == "Hello World"
        assert markdown_comment_content.find_element(By.TAG_NAME, "h2") is not None

        width, height = self.get_element_size(editor.comment._.wait_for_visible())

        assert width == 200
        assert height == 220

        editor.comment.markdown_rendered.wait_for_and_click()
        editor.comment.delete.wait_for_and_click()
        editor.comment.markdown_comment.wait_for_absent()

        # place and test frame comment
        editor.tool_bar.tool(tool="frame_comment").wait_for_and_click()
        editor.tool_bar.color(color="blue").wait_for_and_click()
        self.mouse_drag(from_element=canvas, from_offset=(-200, -150), to_offset=(400, 300))
        self.action_chains().send_keys("My Frame").perform()

        title: WebElement = editor.comment.frame_title.wait_for_visible()
        assert title.text == "My Frame"

        width, height = self.get_element_size(editor.comment._.wait_for_visible())

        assert width == 400
        assert height == 300

        editor.comment.frame_comment.wait_for_and_click()
        editor.comment.delete.wait_for_and_click()
        editor.comment.frame_comment.wait_for_absent()

        # test freehand and eraser
        editor.tool_bar.tool(tool="freehand_pen").wait_for_and_click()
        editor.tool_bar.color(color="green").wait_for_and_click()
        editor.tool_bar.line_thickness.wait_for_and_click()
        self.action_chains().send_keys(Keys.RIGHT * 20).perform()

        editor.tool_bar.smoothing.wait_for_and_click()
        self.action_chains().send_keys(Keys.RIGHT * 10).perform()

        self.mouse_drag(from_element=canvas, from_offset=(-100, -100), to_offset=(200, 200))

        editor.comment.freehand_comment.wait_for_visible()

        editor.tool_bar.color(color="black").wait_for_and_click()
        editor.tool_bar.line_thickness.wait_for_and_click()
        self.action_chains().send_keys(Keys.LEFT * 20).perform()
        self.mouse_drag(from_element=canvas, from_offset=(-100, -100), via_offsets=[(100, 200)], to_offset=(-200, 30))

        # test bulk remove freehand
        editor.tool_bar.remove_freehand.wait_for_and_click()
        editor.comment.freehand_comment.wait_for_absent()

        # place another freehand comment and test eraser
        editor.tool_bar.line_thickness.wait_for_and_click()
        self.action_chains().send_keys(Keys.RIGHT * 20).perform()
        editor.tool_bar.color(color="orange").wait_for_and_click()

        self.mouse_drag(from_element=canvas, from_offset=(-100, -100), to_offset=(200, 200))

        freehand_comment_a: WebElement = editor.comment.freehand_comment.wait_for_visible()

        # delete by clicking
        editor.tool_bar.tool(tool="freehand_eraser").wait_for_and_click()
        self.action_chains().move_to_element(freehand_comment_a).click().perform()

        editor.comment.freehand_comment.wait_for_absent()

        # delete by dragging
        editor.tool_bar.tool(tool="freehand_pen").wait_for_and_click()
        editor.tool_bar.color(color="yellow").wait_for_and_click()

        self.mouse_drag(from_element=canvas, from_offset=(-100, -100), to_offset=(200, 200))

        freehand_comment_b: WebElement = editor.comment.freehand_comment.wait_for_visible()

        editor.tool_bar.tool(tool="freehand_eraser").wait_for_and_click()
        self.mouse_drag(
            from_element=freehand_comment_b, from_offset=(100, -100), via_offsets=[(-100, 100)], to_offset=(-100, 100)
        )

        editor.comment.freehand_comment.wait_for_absent()

    @selenium_test
    def test_editor_snapping(self):
        editor = self.components.workflow_editor
        self.workflow_create_new(annotation="simple workflow")
        self.sleep_for(self.wait_types.UX_RENDER)

        editor.tool_menu.wait_for_visible()

        self.tool_open("cat")
        self.sleep_for(self.wait_types.UX_RENDER)
        editor.label_input.wait_for_and_send_keys("tool_node")

        # activate snapping and set it to max (200)
        editor.tool_bar.tool(tool="toggle_snap").wait_for_and_click()
        editor.tool_bar.snapping_distance.wait_for_and_click()
        self.action_chains().send_keys(Keys.RIGHT * 10).perform()

        # move the node a bit
        tool_node = editor.node._(label="tool_node").wait_for_present()
        self.action_chains().move_to_element(tool_node).click_and_hold().move_by_offset(12, 3).release().perform()

        # check if editor position is snapped
        top, left = self.get_node_position("tool_node")

        assert top % 200 == 0
        assert left % 200 == 0

        # move the node a bit more
        tool_node = editor.node._(label="tool_node").wait_for_present()
        self.action_chains().move_to_element(tool_node).click_and_hold().move_by_offset(207, -181).release().perform()

        # check if editor position is snapped
        top, left = self.get_node_position("tool_node")

        assert top % 200 == 0
        assert left % 200 == 0

    @selenium_test
    def test_editor_selection(self):
        editor = self.components.workflow_editor
        self.workflow_create_new(annotation="simple workflow")
        self.sleep_for(self.wait_types.UX_RENDER)

        canvas = editor.canvas_body.wait_for_visible()

        # place tool in center of canvas
        self.tool_open("cat")
        self.sleep_for(self.wait_types.UX_RENDER)
        editor.label_input.wait_for_and_send_keys("tool_node")
        tool_node = editor.node._(label="tool_node").wait_for_present()
        self.mouse_drag(from_element=tool_node, to_element=canvas, to_offset=(0, -100))

        # select the node
        self.action_chains().move_to_element(tool_node).key_down(Keys.SHIFT).click().key_up(Keys.SHIFT).perform()
        self.sleep_for(self.wait_types.UX_RENDER)

        assert editor.tool_bar.selection_count.wait_for_visible().text.find("1 step") != -1

        # duplicate it
        editor.tool_bar.duplicate_selection.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        assert editor.tool_bar.selection_count.wait_for_visible().text.find("1 step") != -1

        # move the node
        tool_node_new = editor.node._(label="tool_node 2").wait_for_present()
        self.mouse_drag(from_element=tool_node_new, to_element=canvas, to_offset=(0, 100))

        # clear selection
        editor.tool_bar.clear_selection.wait_for_and_click()
        editor.tool_bar.selection_count.wait_for_absent_or_hidden()

        # select both using box
        tool_node_original = editor.node._(label="tool_node").wait_for_present()
        editor.tool_bar.tool(tool="box_select").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.mouse_drag(
            from_element=tool_node_original, from_offset=(150, -100), to_element=tool_node_new, to_offset=(-150, 100)
        )
        self.sleep_for(self.wait_types.UX_RENDER)

        assert editor.tool_bar.selection_count.wait_for_visible().text.find("2 steps") != -1

        # delete steps
        editor.tool_bar.delete_selection.wait_for_and_click()
        editor.tool_bar.selection_count.wait_for_absent_or_hidden()
        editor.node._(label="tool_node").wait_for_absent()
        editor.node._(label="tool_node 2").wait_for_absent()

        # place comments
        editor.tool_bar.tool(tool="text_comment").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.mouse_drag(from_element=canvas, from_offset=(-100, -200), to_element=canvas, to_offset=(100, 0))

        editor.tool_bar.tool(tool="markdown_comment").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.mouse_drag(from_element=canvas, from_offset=(-100, 0), to_element=canvas, to_offset=(100, 200))

        # select both using box select
        editor.tool_bar.tool(tool="box_select").wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.mouse_drag(from_element=canvas, from_offset=(-110, -210), to_element=canvas, to_offset=(110, 210))

        assert editor.tool_bar.selection_count.wait_for_visible().text.find("2 comments") != -1

        # deselect one using box select
        editor.tool_bar.select_mode_remove.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        self.mouse_drag(from_element=canvas, from_offset=(-110, -210), to_element=canvas, to_offset=(110, 10))
        self.sleep_for(self.wait_types.UX_RENDER)

        assert editor.tool_bar.selection_count.wait_for_visible().text.find("1 comment") != -1

    def create_and_wait_for_new_workflow_in_editor(self, annotation: Optional[str] = None) -> str:
        editor = self.components.workflow_editor
        name = self.workflow_create_new(annotation=annotation)
        editor.canvas_body.wait_for_visible()
        return name

    def save_after_node_form_changes(self):
        # onSetData does an extra POST to build_modules, so we need to wait for that ...
        self.sleep_for(self.wait_types.UX_RENDER)
        self.assert_workflow_has_changes_and_save()

    def get_node_position(self, label: str):
        node = self.components.workflow_editor.node._(label=label).wait_for_present()

        return self.get_element_position(node)

    def get_element_position(self, element: WebElement):
        left = element.value_of_css_property("left")
        top = element.value_of_css_property("top")

        left_stripped = "".join(char for char in left if char.isdigit())
        top_stripped = "".join(char for char in top if char.isdigit())

        return (int(left_stripped), int(top_stripped))

    def get_element_size(self, element: WebElement):
        width = element.value_of_css_property("width")
        height = element.value_of_css_property("height")

        width_stripped = "".join(char for char in width if char.isdigit())
        height_stripped = "".join(char for char in height if char.isdigit())

        return (int(width_stripped), int(height_stripped))

    def assert_node_output_is(self, label: str, output_type: str, subcollection_type: Optional[str] = None):
        editor = self.components.workflow_editor
        node_label, output_name = label.split("#")
        node = editor.node._(label=node_label)
        node.wait_for_present()
        output_element = node.output_terminal(name=output_name).wait_for_visible()
        self.hover_over(output_element)
        element = self.components._.tooltip_inner.wait_for_present()
        assert f"output is {output_type}" in element.text, element.text
        if subcollection_type is None:
            assert "mapped-over" not in element.text
        else:
            fragment = " and mapped-over to produce a "
            if subcollection_type == "list:paired":
                fragment += "list of pairs dataset collection"
            elif subcollection_type == "list:list":
                fragment += "list of lists dataset collection"
            elif subcollection_type.count(":") > 1:
                fragment += f"dataset collection with {subcollection_type.count(':') + 1} levels of nesting"
            else:
                fragment += f"{subcollection_type}"
            assert fragment in element.text
        self.click_center()

    def workflow_editor_maximize_center_pane(self, collapse_left=True, collapse_right=True):
        if collapse_left:
            self.hover_over(self.components._.left_panel_drag.wait_for_visible())
            self.components._.left_panel_collapse.wait_for_and_click()
        if collapse_right:
            self.hover_over(self.components._.right_panel_drag.wait_for_visible())
            self.components._.right_panel_collapse.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

    def workflow_editor_connect(self, source, sink, screenshot_partial=None):
        source_id, sink_id = self.workflow_editor_source_sink_terminal_ids(source, sink)
        source_element = self.find_element_by_selector(f"#{source_id}")
        sink_element = self.find_element_by_selector(f"#{sink_id}")
        ac = self.action_chains()
        ac = ac.move_to_element(source_element).click_and_hold()
        if screenshot_partial:
            ac = ac.move_by_offset(10, 10)
            ac.perform()
            self.sleep_for(self.wait_types.UX_RENDER)
            self.screenshot(screenshot_partial)
        drag_and_drop(self.driver, source_element, sink_element)

    def assert_connected(self, source, sink):
        source_id, sink_id = self.workflow_editor_source_sink_terminal_ids(source, sink)
        self.components.workflow_editor.connector_for(source_id=source_id, sink_id=sink_id).wait_for_visible()

    def assert_connection_invalid(self, source, sink):
        source_id, sink_id = self.workflow_editor_source_sink_terminal_ids(source, sink)
        self.components.workflow_editor.connector_invalid_for(source_id=source_id, sink_id=sink_id).wait_for_present()

    def assert_not_connected(self, source, sink):
        source_id, sink_id = self.workflow_editor_source_sink_terminal_ids(source, sink)
        self.components.workflow_editor.connector_for(source_id=source_id, sink_id=sink_id).wait_for_absent()

    def open_in_workflow_editor(self, yaml_content, auto_layout=True):
        name = self.workflow_upload_yaml_with_random_name(yaml_content)
        self.workflow_index_open()
        self.workflow_index_open_with_name(name)
        if auto_layout:
            self.workflow_editor_click_option("Auto Layout")
            self.sleep_for(self.wait_types.UX_RENDER)
        return name

    def workflow_editor_source_sink_terminal_ids(self, source, sink):
        editor = self.components.workflow_editor

        source_node_label, source_output = source.split("#", 1)
        sink_node_label, sink_input = sink.split("#", 1)

        source_node = editor.node._(label=source_node_label)
        sink_node = editor.node._(label=sink_node_label)

        source_node.wait_for_present()
        sink_node.wait_for_present()

        output_terminal = source_node.output_terminal(name=source_output)
        input_terminal = sink_node.input_terminal(name=sink_input)

        output_element = output_terminal.wait_for_present()
        input_element = input_terminal.wait_for_present()

        source_id = output_element.get_attribute("id").replace("|", r"\|")
        sink_id = input_element.get_attribute("id").replace("|", r"\|")

        return source_id, sink_id

    def workflow_editor_destroy_connection(self, sink):
        editor = self.components.workflow_editor

        sink_node_label, sink_input_name = sink.split("#", 1)
        sink_node = editor.node._(label=sink_node_label)
        sink_input = sink_node.input_terminal(name=sink_input_name).wait_for_visible()
        self.hover_over(sink_input)
        sink_node.connector_destroy_callout(name=sink_input_name).wait_for_and_click()

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
        self.components.workflows.edit_button.wait_for_and_click()

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

    def move_center_of_canvas(self, xoffset=0, yoffset=0):
        canvas = self.find_element_by_id("canvas-container")
        chains = ActionChains(self.driver)
        chains.click_and_hold(canvas).move_by_offset(xoffset=xoffset, yoffset=yoffset).release().perform()

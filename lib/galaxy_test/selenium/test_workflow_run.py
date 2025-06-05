import json
from uuid import uuid4

import yaml
from selenium.webdriver.common.by import By
from typing_extensions import Literal

from galaxy_test.base import rules_test_data
from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_LIST_PAIRED_MAPPED_OVER_PAIRED,
    WORKFLOW_LIST_PAIRED_OR_UNPAIRED_INPUT,
    WORKFLOW_NESTED_REPLACEMENT_PARAMETER,
    WORKFLOW_NESTED_RUNTIME_PARAMETER,
    WORKFLOW_NESTED_SIMPLE,
    WORKFLOW_RENAME_ON_REPLACEMENT_PARAM,
    WORKFLOW_RUNTIME_PARAMETER_SIMPLE,
    WORKFLOW_SELECT_FROM_OPTIONAL_DATASET,
    WORKFLOW_SIMPLE_CAT_TWICE,
    WORKFLOW_WITH_CUSTOM_REPORT_1,
    WORKFLOW_WITH_CUSTOM_REPORT_1_TEST_DATA,
    WORKFLOW_WITH_DATA_TAG_FILTER,
    WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION,
    WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION,
    WORKFLOW_WITH_OLD_TOOL_VERSION,
    WORKFLOW_WITH_RULES_1,
)
from .framework import (
    managed_history,
    RunsWorkflows,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)


class TestWorkflowRun(SeleniumTestCase, UsesHistoryItemAssertions, RunsWorkflows):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_workflow_export_file_rocrate(self):
        self._setup_simple_invocation_for_export_testing()
        invocations = self.components.invocations
        self.workflow_run_wait_for_ok(hid=2)
        invocations.export_tab_disabled.wait_for_absent()
        invocations.export_tab.wait_for_and_click()
        self.screenshot("invocation_export_formats")
        invocations.export_output_format(type="ro-crate").wait_for_and_click()
        invocations.wizard_next_button.wait_for_and_click()
        download_option = invocations.export_destination(destination="download")
        download_option.wait_for_present()
        self.screenshot("invocation_export_rocrate_destinations")
        download_option.wait_for_and_click()
        invocations.wizard_next_button.wait_for_and_click()
        export_button = invocations.wizard_export_button
        export_button.wait_for_present()
        self.screenshot("invocation_export_rocrate_download_options")
        export_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("invocation_export_crate_preparing_download")
        invocations.export_download_link.wait_for_present()
        self.screenshot("invocation_export_crate_download_ready")

    @selenium_test
    @managed_history
    def test_workflow_export_file_native(self):
        self._setup_simple_invocation_for_export_testing()
        invocations = self.components.invocations
        self.workflow_run_wait_for_ok(hid=2)
        invocations.export_tab_disabled.wait_for_absent()
        invocations.export_tab.wait_for_and_click()
        self.screenshot("invocation_export_formats")
        invocations.export_output_format(type="default-file").wait_for_and_click()
        invocations.wizard_next_button.wait_for_and_click()
        download_option = invocations.export_destination(destination="download")
        download_option.wait_for_present()
        self.screenshot("invocation_export_native_destinations")
        download_option.wait_for_and_click()
        invocations.wizard_next_button.wait_for_and_click()
        export_button = invocations.wizard_export_button
        export_button.wait_for_present()
        self.screenshot("invocation_export_native_download_options")
        export_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("invocation_export_native_preparing_download")
        invocations.export_download_link.wait_for_present()
        self.screenshot("invocation_export_native_download_ready")

    @selenium_test
    @managed_history
    def test_simple_execution(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.screenshot("workflow_run_simple_ready")
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("workflow_run_simple_submitted")
        self.workflow_run_wait_for_ok(hid=2, expand=True)
        self.assert_item_summary_includes(2, "2 sequences")
        self.screenshot("workflow_run_simple_complete")

    @selenium_test
    @managed_history
    def test_expanded_execution_of_simple_workflow(self):
        self.perform_upload(self.get_filename("1.fasta"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.workflow_run_ensure_expanded()
        self.screenshot("workflow_run_expanded_ready")
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("workflow_run_expanded_submitted")
        self.workflow_run_wait_for_ok(hid=2, expand=True)
        self.assert_item_summary_includes(2, "2 sequences")
        self.screenshot("workflow_run_simple_complete")

    @selenium_test
    @managed_history
    def test_runtime_parameters_simple(self):
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_RUNTIME_PARAMETER_SIMPLE)
        self.tool_parameter_div("num_lines")
        self.screenshot("workflow_run_runtime_parameters_initial")
        self._set_num_lines_to_3("num_lines")
        self.screenshot("workflow_run_runtime_parameters_modified")
        self.workflow_run_submit()

        self._assert_has_3_lines_after_run(hid=2)

    @selenium_test
    @managed_history
    def test_runtime_parameters_simple_optional(self):
        self.workflow_run_open_workflow(
            """
class: GalaxyWorkflow
inputs: {}
steps:
  int_step:
    tool_id: expression_null_handling_integer
    runtime_inputs:
      - int_input
"""
        )
        self.tool_parameter_div("int_input")
        self._set_num_lines_to_3("int_input")
        self.screenshot("workflow_run_optional_runtime_parameters_modified")
        self.workflow_run_submit()
        self.workflow_run_wait_for_ok(hid=1)
        history_id = self.current_history_id()
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=1)
        assert json.loads(content) == 3

    @selenium_test
    @managed_history
    def test_subworkflows_expanded(self):
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_NESTED_SIMPLE)
        self.workflow_run_ensure_expanded()
        self.components.workflow_run.subworkflow_step_icon.wait_for_visible()
        self.screenshot("workflow_run_nested_collapsed")
        self.components.workflow_run.subworkflow_step_icon.wait_for_and_click()
        self.screenshot("workflow_run_nested_open")

    @selenium_test
    @managed_history
    def test_subworkflow_runtime_parameters(self):
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_NESTED_RUNTIME_PARAMETER)
        self.workflow_run_ensure_expanded()
        self.components.workflow_run.subworkflow_step_icon.wait_for_visible()
        self.screenshot("workflow_run_nested_parameters_collapsed")
        self.components.workflow_run.subworkflow_step_icon.wait_for_and_click()
        self.screenshot("workflow_run_nested_parameters_open")
        self._set_num_lines_to_3("1|num_lines")
        self.workflow_run_submit()

        self._assert_has_3_lines_after_run(hid=2)

    @selenium_test
    @managed_history
    def test_replacement_parameters(self):
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_RENAME_ON_REPLACEMENT_PARAM)
        self.workflow_run_ensure_expanded()
        self.screenshot("workflow_run_rename_simple_empty")
        self._set_replacement_parameter("replaceme", "moocow")
        self.screenshot("workflow_run_rename_simple_input")
        self.workflow_run_submit()
        output_hid = 2
        self.workflow_run_wait_for_ok(hid=output_hid)
        history_id = self.current_history_id()
        details = self.dataset_populator.get_history_dataset_details(history_id, hid=output_hid)
        assert details["name"] == "moocow suffix", details

    @selenium_test
    @managed_history
    def test_step_parameter_inputs(self):
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.workflow_run_open_workflow(
            """
class: GalaxyWorkflow
inputs:
  input_int: integer
  input_data: data
steps:
  simple_constructs:
    tool_id: simple_constructs
    label: tool_exec
    in:
      inttest: input_int
      files_0|file: input_data
"""
        )
        self.workflow_run_ensure_expanded()
        workflow_run = self.components.workflow_run
        input_div_element = workflow_run.input_div(label="input_int").wait_for_visible()
        input_element = input_div_element.find_element(By.CSS_SELECTOR, "input")
        input_element.clear()
        input_element.send_keys("12345")

        self.screenshot("workflow_run_step_parameter_input")
        self.workflow_run_submit()
        output_hid = 2
        self.workflow_run_wait_for_ok(hid=output_hid)
        history_id = self.current_history_id()
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=output_hid)
        assert "12345" in content, content
        assert "chr6_hla_hap2" in content

    @selenium_test
    @managed_history
    def test_replacement_parameters_on_subworkflows(self):
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_NESTED_REPLACEMENT_PARAMETER)
        self.workflow_run_ensure_expanded()
        self.screenshot("workflow_run_rename_subworkflow_empty")
        self._set_replacement_parameter("replaceme", "moocow")
        self.screenshot("workflow_run_rename_subworkflow_input")
        self.workflow_run_submit()
        output_hid = 2
        self.workflow_run_wait_for_ok(hid=output_hid)
        history_id = self.current_history_id()
        details = self.dataset_populator.get_history_dataset_details(history_id, hid=output_hid)
        assert details["name"] == "moocow suffix", details

    @selenium_test
    def test_execution_with_tool_upgrade(self):
        name = self.workflow_upload_yaml_with_random_name(WORKFLOW_WITH_OLD_TOOL_VERSION, exact_tools=True)
        self.workflow_run_with_name(name)
        self.sleep_for(self.wait_types.UX_TRANSITION)
        # Check that this tool form contains a warning about different versions.
        self.assert_message(self.components.workflow_run.warning, contains="tools which have changed")
        self.screenshot("workflow_run_tool_upgrade")

    @selenium_test
    def test_run_form_safe_upgrade_handling(self):
        workflow_with_rules = yaml.safe_load(WORKFLOW_WITH_RULES_1)
        # 0.9.0 is a version that does not exist in WORKFLOW_SAFE_TOOL_VERSION_UPDATES
        workflow_with_rules["steps"]["apply"]["tool_version"] = "0.9.0"
        workflow_with_rules_json = json.dumps(workflow_with_rules)
        name = self.workflow_upload_yaml_with_random_name(workflow_with_rules_json, exact_tools=True)
        self.workflow_run_with_name(name)
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.assert_message(self.components.workflow_run.warning, contains="tools which have changed")
        # 1.0.0 is a version that exists in WORKFLOW_SAFE_TOOL_VERSION_UPDATES
        workflow_with_rules["steps"]["apply"]["tool_version"] = "1.0.0"
        workflow_with_rules_json = json.dumps(workflow_with_rules)
        name = self.workflow_upload_yaml_with_random_name(workflow_with_rules_json, exact_tools=True)
        self.workflow_run_with_name(name)
        self.sleep_for(self.wait_types.UX_TRANSITION)
        # Check that this tool form does not contain a warning about different versions.
        assert self.components.workflow_run.warning.is_absent

    @selenium_test
    @managed_history
    def test_execution_with_multiple_inputs(self):
        history_id = self.workflow_run_and_submit(
            WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION,
            WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION,
            inputs_specified_screenshot_name="workflow_run_two_inputs",
            ensure_expanded=True,
        )
        self.workflow_run_wait_for_ok(hid=7)
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=7)
        assert "10.0\n30.0\n20.0\n40.0\n" == content

    @selenium_test
    @managed_history
    def test_execution_with_text_default_value_connected_to_restricted_select(self):
        self.workflow_run_open_workflow(
            """
class: GalaxyWorkflow
inputs:
  text_param:
    optional: true
    default: ex2
    restrictOnConnections: true
    type: text
steps:
  multi_select:
    tool_id: multi_select
    in:
      select_ex:
        source: text_param
"""
        )
        element = self.components.workflow_run.input_select_field(label="text_param").wait_for_present()
        assert element.text == "Ex2"
        self.workflow_run_submit()
        history_id = self.current_history_id()
        self.workflow_populator.wait_for_history_workflows(history_id, expected_invocation_count=1)
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=1)
        assert content == "ex2"

    @selenium_test
    @managed_history
    def test_execution_with_rules(self):
        history_id = self.workflow_run_and_submit(
            WORKFLOW_WITH_RULES_1,
            WORKFLOW_WITH_RULES_1,
            landing_screenshot_name="workflow_run_rules_landing",
            inputs_specified_screenshot_name="workflow_run_rules",
            ensure_expanded=True,
        )
        self.workflow_run_wait_for_ok(hid=6)
        output_content = self.dataset_populator.get_history_collection_details(history_id, hid=6)
        rules_test_data.check_example_2(output_content, self.dataset_populator)

    @selenium_test
    @managed_history
    def test_execution_with_custom_invocation_report(self):
        history_id = self.workflow_run_and_submit(
            WORKFLOW_WITH_CUSTOM_REPORT_1,
            WORKFLOW_WITH_CUSTOM_REPORT_1_TEST_DATA,
            ensure_expanded=True,
        )
        self.screenshot("workflow_run_invocation_report")
        self.workflow_populator.wait_for_history_workflows(history_id, expected_invocation_count=1)
        invocation_0 = self.workflow_populator.history_invocations(history_id)[0]
        self.get(f"workflows/invocations/report?id={invocation_0['id']}")
        self.wait_for_selector_visible(".markdown-component")
        self.screenshot("workflow_report_custom_1")

    @selenium_test
    @managed_history
    def test_execution_with_null_optional_select_from_data(self):
        history_id = self.workflow_run_and_submit(
            WORKFLOW_SELECT_FROM_OPTIONAL_DATASET,
        )
        self.workflow_populator.wait_for_history_workflows(history_id, expected_invocation_count=1)

    @selenium_test
    @managed_history
    def test_workflow_run_button_disabled_when_required_input_missing(self):
        self.workflow_run_open_workflow(
            """
class: GalaxyWorkflow
inputs:
  text_param:
    type: text
    optional: false
  data_param:
    type: data
  collection_param:
    type: data_collection
steps: {}
"""
        )
        workflow_run = self.components.workflow_run
        # None of the required parameters are present
        workflow_run.run_workflow_disabled.wait_for_present()
        # upload datasets and collections
        history_id = self.current_history_id()
        self.dataset_populator.new_dataset(history_id, wait=True)
        self.dataset_collection_populator.create_list_in_history(history_id, wait=True)
        input_element = workflow_run.simplified_input(label="text_param").wait_for_and_click()
        input_element.send_keys("3")
        # Everything is set, workflow is runnable, disabled class should be removed
        workflow_run.run_workflow_disabled.wait_for_absent()
        input_element.clear()
        workflow_run.run_workflow_disabled.wait_for_present()

    @selenium_test
    @managed_history
    def test_workflow_run_tag_filter(self):
        history_id = self.current_history_id()
        dataset = self.dataset_populator.new_dataset(history_id, wait=True)
        self.dataset_populator.tag_dataset(history_id, dataset["id"], tags=["genomescope_model"])
        # Add another possible input that should not be selected
        self.dataset_populator.new_dataset(history_id, wait=True)
        workflow_id, workflow_name = self._create_workflow_with_unique_name(WORKFLOW_WITH_DATA_TAG_FILTER, "ga")
        self.workflow_run_with_name(workflow_name)
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.HISTORY_POLL)
        invocations = self.workflow_populator.workflow_invocations(workflow_id=workflow_id)
        invocation = self.workflow_populator.get_invocation(invocations[-1]["id"])
        assert invocation["inputs"]["0"]["id"] == dataset["id"]

    @selenium_test
    @managed_history
    def test_workflow_run_list_paired_or_unpaired_with_paired_list(self):
        history_id = self.current_history_id()
        self.perform_upload_of_pasted_content(
            {
                "foo_1.fasta": "forward content",
                "foo_2.fasta": "reverse content",
            }
        )
        self.history_panel_wait_for_and_select([1, 2])
        self.history_panel_build_list_of_pairs()
        self.collection_builder_set_name("my awesome paired list")
        self.collection_builder_create()
        self.history_panel_wait_for_hid_ok(5)
        self._create_and_run_workflow_with_unique_name(WORKFLOW_LIST_PAIRED_OR_UNPAIRED_INPUT)
        self.workflow_run_submit()
        self.history_panel_wait_for_hid_ok(6)
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=6)
        assert content.strip() == "forward content\nreverse content"

    @selenium_test
    @managed_history
    def test_workflow_run_list_paired_or_unpaired_with_flat_list(self):
        history_id = self.current_history_id()
        self.perform_upload_of_pasted_content(
            {
                "foo_1.fasta": "forward content",
                "foo_2.fasta": "reverse content",
            }
        )
        self.history_panel_wait_for_and_select([1, 2])
        self.history_panel_build_list_advanced_and_select_builder("list")
        self.collection_builder_set_name("my awesome flat list")
        self.collection_builder_create()
        self.history_panel_wait_for_hid_ok(5)
        self._create_and_run_workflow_with_unique_name(WORKFLOW_LIST_PAIRED_OR_UNPAIRED_INPUT)
        self.workflow_run_submit()
        self.history_panel_wait_for_hid_ok(6)
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=6)
        assert content.strip() == "reverse content\nforward content"

    @selenium_test
    @managed_history
    def test_workflow_run_list_paired_or_unpaired_with_mixed_list(self):
        history_id = self.current_history_id()
        self.perform_upload_of_pasted_content(
            {
                "foo_1.fasta": "forward content",
                "foo_2.fasta": "reverse content",
                "other.fasta": "unpaired content",
            }
        )
        self.history_panel_wait_for_and_select([1, 2, 3])
        self.history_panel_build_list_of_paired_or_unpaireds()
        self.collection_builder_set_name("my awesome flat list")
        self.collection_builder_create()
        self.history_panel_wait_for_hid_ok(7)
        self._create_and_run_workflow_with_unique_name(WORKFLOW_LIST_PAIRED_OR_UNPAIRED_INPUT)
        self.workflow_run_submit()
        self.history_panel_wait_for_hid_ok(8)
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=8)
        assert content.strip() == "forward content\nreverse content\nunpaired content"

    @selenium_test
    @managed_history
    def test_upload_dataset_from_workflow_simple(self):
        history_id = self.current_history_id()
        self._create_and_run_workflow_with_unique_name(WORKFLOW_SIMPLE_CAT_TWICE)
        workflow_run = self.components.workflow_run
        input = workflow_run.input._(label="input1")
        input.upload.wait_for_and_click()
        self._upload_hello_world_for_input(input)
        self.workflow_run_submit()
        self.history_panel_wait_for_hid_ok(2)
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=2)
        assert content.strip() == "hello world\nhello world"

    @selenium_test
    @managed_history
    def test_modal_upload_updates_form(self):
        history_id = self.current_history_id()
        self.perform_upload_of_pasted_content("goodbye land")

        self._create_and_run_workflow_with_unique_name(WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION)
        workflow_run = self.components.workflow_run
        input = workflow_run.input._(label="input1")
        input.upload.wait_for_and_click()

        self.perform_upload_of_pasted_content("hello world", on_current_page=True)

        self.history_panel_wait_for_hid_ok(2)

        builder = workflow_run.input.collection_builder._(label="input1")
        # it is a div so I don't think it works to click directly but we can go to it and click
        # on that part of the screen.
        element = builder.element_by_hid(hid=2).wait_for_present()
        action_chains = self.action_chains()
        action_chains.move_to_element(element)
        action_chains.click()
        action_chains.perform()

        input.collection_tab_build_link.wait_for_and_click()
        builder.create.wait_for_and_click()

        self.workflow_run_submit()
        self.history_panel_wait_for_hid_ok(5)
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=6)
        assert content.strip() == "hello world"

    @selenium_test
    @managed_history
    def test_upload_list_from_workflow_simple(self):
        self._create_and_run_workflow_with_unique_name(WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION)
        workflow_run = self.components.workflow_run
        input = workflow_run.input._(label="input1")
        input.upload.wait_for_and_click()
        input.collection_tab_upload_link.wait_for_and_click()
        builder = workflow_run.input.collection_builder._(label="input1")
        self._upload_hello_world_for_input(builder, count=2)
        input.collection_tab_build_link.wait_for_and_click()
        builder.create.wait_for_and_click()
        self.workflow_run_submit()
        self.history_panel_wait_for_hid_ok(6)

    @selenium_test
    @managed_history
    def test_upload_list_paired_from_workflow(self):
        history_id = self.current_history_id()
        self._create_and_run_workflow_with_unique_name(WORKFLOW_LIST_PAIRED_MAPPED_OVER_PAIRED)
        workflow_run = self.components.workflow_run
        input = workflow_run.input._(label="input_list")
        input.upload.wait_for_and_click()
        input.collection_tab_upload_link.wait_for_and_click()
        builder = workflow_run.input.collection_builder._(label="input_list")
        self._upload_hello_world_for_input(builder, count=2)
        input.collection_tab_build_link.wait_for_and_click()
        builder.create.wait_for_and_click()
        self.workflow_run_submit()
        self.history_panel_wait_for_hid_ok(6)
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=7)
        assert content.strip() == "hello world\nhello world"

    @selenium_test
    @managed_history
    def test_upload_list_paired_or_unpaired_from_workflow(self):
        history_id = self.current_history_id()
        self.perform_upload_of_pasted_content(
            {
                "foo_1.fasta": "forward content",
                "foo_2.fasta": "reverse content",
                "other.fasta": "unpaired content",
            }
        )
        self.history_panel_wait_for_hid_ok(3)
        self._create_and_run_workflow_with_unique_name(WORKFLOW_LIST_PAIRED_OR_UNPAIRED_INPUT)
        workflow_run = self.components.workflow_run
        input = workflow_run.input._(label="input_list")
        input.upload.wait_for_and_click()
        builder = workflow_run.input.collection_builder._(label="input_list")
        builder.element_by_hid(hid=3).wait_for_present()
        # self.sleep_for(self.wait_types.UX_TRANSITION)
        builder.select_all.wait_for_and_click()
        input.collection_tab_build_link.wait_for_and_click()
        builder.create.wait_for_and_click()
        self.workflow_run_submit()

        self.history_panel_wait_for_hid_ok(8)
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=8)
        assert content.strip() == "unpaired content\nreverse content\nforward content"

    def _upload_hello_world_for_input(self, workflow_input, count=1, from_hid=1):
        # assumes fresh history...
        for i in range(count):
            workflow_input.create_button.wait_for_and_click()
            url = self.dataset_populator.base64_url_for_string("hello world")
            workflow_input.paste_content(n=i).wait_for_and_send_keys(url)
            workflow_input.title(n=i).wait_for_and_clear_and_send_keys(f"hello world.{i + 1}.fastq")

        workflow_input.embedded_start_button.wait_for_and_click()
        workflow_input.use_button.wait_for_and_click()

    def _create_and_run_workflow_with_unique_name(
        self, workflow_contents: str, format: Literal["ga", "gxformat2"] = "gxformat2"
    ):
        workflow_id, workflow_name = self._create_workflow_with_unique_name(workflow_contents, format)
        self.workflow_run_with_name(workflow_name)
        return workflow_id, workflow_name

    def _create_workflow_with_unique_name(
        self, workflow_contents: str, format: Literal["ga", "gxformat2"] = "gxformat2"
    ):
        workflow_name = str(uuid4())
        if format == "gxformat2":
            wf = yaml.safe_load(workflow_contents)
            wf["name"] = workflow_name
            workflow_id = self.workflow_populator.upload_yaml_workflow(wf)
        else:
            wf = json.loads(workflow_contents)
            wf["name"] = workflow_name
            workflow_id = self.workflow_populator.create_workflow(wf)
        return (workflow_id, workflow_name)

    def _assert_has_3_lines_after_run(self, hid):
        self.workflow_run_wait_for_ok(hid=hid)
        history_id = self.current_history_id()
        content = self.dataset_populator.get_history_dataset_content(history_id, hid=hid)
        assert len([x for x in content.split("\n") if x]) == 3, content

    def _set_num_lines_to_3(self, element_id):
        # for random_lines num_lines parameter as runtime parameter in workflow form.
        div = self.tool_parameter_div(element_id)
        input_element = div.find_element(By.CSS_SELECTOR, "input")
        # runtime parameters not being set to tool default value:
        # https://github.com/galaxyproject/galaxy/pull/7157
        # initial_value = input_element.get_attribute("value")
        # assert initial_value == "1", initial_value
        input_element.clear()
        input_element.send_keys("3")

    def _set_replacement_parameter(self, element_id, value):
        # for random_lines num_lines parameter as runtime parameter in workflow form.
        div = self.tool_parameter_div(element_id)
        input_element = div.find_element(By.CSS_SELECTOR, "input")
        initial_value = input_element.get_attribute("value")
        assert initial_value == "", initial_value
        input_element.clear()
        input_element.send_keys(value)

    def _setup_simple_invocation_for_export_testing(self):
        # precondition: refresh history
        self.perform_upload(self.get_filename("1.fasta"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.workflow_run_submit()
        history_id = self.current_history_id()
        self.workflow_populator.wait_for_history_workflows(history_id, expected_invocation_count=1)
        return self.workflow_populator.history_invocations(history_id)[0]

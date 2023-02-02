from selenium.webdriver.common.by import By

from galaxy_test.base import rules_test_data
from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_NESTED_REPLACEMENT_PARAMETER,
    WORKFLOW_NESTED_RUNTIME_PARAMETER,
    WORKFLOW_NESTED_SIMPLE,
    WORKFLOW_RENAME_ON_REPLACEMENT_PARAM,
    WORKFLOW_RUNTIME_PARAMETER_SIMPLE,
    WORKFLOW_SELECT_FROM_OPTIONAL_DATASET,
    WORKFLOW_SIMPLE_CAT_TWICE,
    WORKFLOW_WITH_CUSTOM_REPORT_1,
    WORKFLOW_WITH_CUSTOM_REPORT_1_TEST_DATA,
    WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION,
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
        self.assert_message(self.components.workflow_run.warning, contains="different versions")
        self.screenshot("workflow_run_tool_upgrade")

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
        self.wait_for_selector_visible(".embedded-dataset")
        self.screenshot("workflow_report_custom_1")

    @selenium_test
    @managed_history
    def test_execution_with_null_optional_select_from_data(self):
        history_id = self.workflow_run_and_submit(
            WORKFLOW_SELECT_FROM_OPTIONAL_DATASET,
        )
        self.workflow_populator.wait_for_history_workflows(history_id, expected_invocation_count=1)

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

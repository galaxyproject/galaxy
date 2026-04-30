from selenium.webdriver.common.by import By

from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    RunsWorkflows,
    selenium_only,
    selenium_test,
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)

WORKFLOW_BOOLEAN_PARAMETER_DEFAULT_TRUE = """
class: GalaxyWorkflow
inputs:
  bool_param:
    type: boolean
    default: true
steps:
  echo_bool:
    tool_id: gx_boolean
    in:
      parameter: bool_param
"""


class TestWorkflowRun(SeleniumTestCase, UsesHistoryItemAssertions, RunsWorkflows):
    ensure_registered = True

    @selenium_only("Not yet migrated to support Playwright backend")
    @selenium_test
    @managed_history
    def test_workflow_rerun(self):
        # Run a workflow first
        self.perform_upload(self.get_filename("1.fasta"))
        self.wait_for_history()
        self.workflow_run_open_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.screenshot("workflow_run_before_rerun_ready")
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.workflow_run_wait_for_ok(hid=2, expand=True)
        self.assert_item_summary_includes(2, "2 sequences")

        # Keep track of the original history name
        original_history_name = self.history_panel_name()

        # Create a new history, different from the original
        self.history_panel_create_new()
        self.home()
        self._assert_history_name_is("Unnamed history")
        assert self.history_panel_name() != original_history_name

        self.screenshot("workflow_run_before_rerun_complete")

        # Route to rerun
        self._invocations_panel_open_latest_invocation()
        self.components.invocations.workflow_rerun_button.wait_for_and_click()

        # Will trigger confirmation modal
        self.components.invocations.change_history_rerun_confirm.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)

        # Arriving on the rerun page, the history should have switched back to the original history
        self._assert_history_name_is(original_history_name)

        self.screenshot("workflow_rerun_ready")

        # Check input has the original dataset name
        form_element = self.components.workflow_run.form_element._(index=0)
        input_element_value = form_element.select_value.wait_for_visible()
        assert (
            "1: 1.fasta" in input_element_value.text
        ), f"Expected input to be 1.fasta but got {input_element_value.text}"

        # Change input value to latest dataset (as it would be if it wasn't a rerun)
        self.select_set_value(form_element.select, "2:")

        # Find that the changed input badge exists
        form_element.changed_value_badge.wait_for_visible()
        self.screenshot("workflow_rerun_changed_input")

    @selenium_test
    @managed_history
    def test_workflow_rerun_preserves_false_boolean_parameter(self):
        """Regression test for boolean workflow parameters reverting to default on rerun.

        Setting a boolean ``parameter_input`` to ``false`` (overriding a
        ``default: true``), running the workflow, and re-running the invocation
        previously caused the form to silently fall back to the default value
        because of a falsy-value check in WorkflowRunFormSimple.vue. The form
        should instead show the value the user actually used.
        """
        invocations = self.components.invocations

        self.workflow_run_open_workflow(WORKFLOW_BOOLEAN_PARAMETER_DEFAULT_TRUE)

        # Override the boolean default of true to false before submitting.
        # The boolean is the workflow's only input, hence step_index 0.
        self._toggle_workflow_run_boolean(parameter="0", target=False)
        self.screenshot("workflow_run_boolean_false_before_submit")

        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.workflow_run_wait_for_ok(hid=1)

        # Submitting lands us on the new invocation page; the rerun button is
        # right there on the invocation state details. We're still in the
        # invocation's history, so no "switch history" confirmation appears.
        invocations.state_details.wait_for_visible()
        invocations.workflow_rerun_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)

        # The boolean should be preserved as false on the rerun form rather than
        # silently reset to the workflow's default of true.
        checkbox = self.components.tool_form.parameter_checkbox_input(parameter="0").wait_for_present()
        assert (
            not checkbox.is_selected()
        ), "Boolean parameter input was reset to its default 'true' instead of preserving the previous run's 'false' value"

        # Without changes, the boolean should not be flagged as a changed input.
        form_element = self.components.workflow_run.form_element._(index=0)
        form_element.changed_value_badge.assert_absent()
        self.screenshot("workflow_rerun_boolean_preserved_false")

        # Toggling the value back to true should flag it as changed.
        self._toggle_workflow_run_boolean(parameter="0", target=True)
        form_element.changed_value_badge.wait_for_visible()
        self.screenshot("workflow_rerun_boolean_changed_input")

        # Submit the rerun and verify the new invocation actually recorded the
        # value shown in the form (true) on its Inputs tab.
        self.workflow_run_submit()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.workflow_run_wait_for_ok(hid=2)
        invocations.state_details.wait_for_visible()
        invocations.invocation_tab(label="Inputs").wait_for_and_click()
        self._assert_input_table_has_parameter("bool_param", "true")
        self.screenshot("workflow_rerun_boolean_inputs_tab")

    @retry_assertion_during_transitions
    def _assert_input_table_has_parameter(self, label: str, value: str):
        table = self.driver.find_element(By.CSS_SELECTOR, '[data-description="input table"]')
        text = table.text
        assert label in text, f"Expected input label '{label}' in inputs table, got: {text!r}"
        assert value in text, f"Expected input value '{value}' in inputs table, got: {text!r}"

    def _toggle_workflow_run_boolean(self, parameter: str, target: bool):
        checkbox = self.components.tool_form.parameter_checkbox_input(parameter=parameter).wait_for_present()
        if checkbox.is_selected() != target:
            self.execute_script("arguments[0].click();", checkbox)

    @retry_assertion_during_transitions
    def _assert_history_name_is(self, expected_name=None):
        name = self.history_panel_name()
        assert name == expected_name, f"History name should be {expected_name} but is {name}"

    def _invocations_panel_open_latest_invocation(self):
        """Open the latest invocation from the invocations panel."""
        invocations = self.components.invocations
        invocations.activity.wait_for_and_click()
        self.components.invocations.invocations_panel_list.wait_for_visible()

        @retry_assertion_during_transitions
        def assert_has_row():
            invocations.invocations_panel_list_items.wait_for_visible()
            invocation_rows = invocations.invocations_panel_list_items.all()
            assert len(invocation_rows) > 0
            return invocation_rows[0]

        assert_has_row()

        invocations.state_details.assert_absent()
        details = invocations.invocations_panel_list_items.all()[0]
        details.click()
        invocations.state_details.wait_for_visible()

        # close invocations panel
        invocations.activity.wait_for_and_click()

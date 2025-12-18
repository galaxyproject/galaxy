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

from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_KEEP_SUCCESSFUL_DATASETS,
    WORKFLOW_KEEP_SUCCESSFUL_DATASETS_TEST_DATA,
    WORKFLOW_WITH_OUTPUT_COLLECTION,
)
from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class TestWorkflowInvocationDetails(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    def test_job_details(self):
        gx_selenium_context = self
        history_id = gx_selenium_context.dataset_populator.new_history()
        gx_selenium_context.workflow_populator.run_workflow(
            WORKFLOW_WITH_OUTPUT_COLLECTION, history_id=history_id, assert_ok=True, wait=True
        )

        self.invocation_open_latest()

        invocations = self.components.invocations

        @retry_assertion_during_transitions
        def assert_progress_steps_note_contains(text):
            assert text in invocations.progress_steps_note.wait_for_visible().text

        assert_progress_steps_note_contains("3 of 3 steps successfully scheduled.")
        assert "2 of 2 jobs complete." in invocations.progress_jobs_note.wait_for_visible().text

        invocations.invocation_tab(label="Inputs").wait_for_and_click()
        invocations.input_details_title(label="text_input").wait_for_visible()
        assert "Test_Dataset" in invocations.input_details_name(label="text_input").wait_for_visible().text

        invocations.invocation_tab(label="Steps").wait_for_and_click()
        assert "Step 1: text_input" in invocations.step_title(order_index="0").wait_for_visible().text
        assert "Step 2: split_up" in invocations.step_title(order_index="1").wait_for_visible().text
        assert "Step 3: paired" in invocations.step_title(order_index="2").wait_for_visible().text

        invocations.step_details(order_index="1").wait_for_and_click()
        invocations.step_job_details(order_index="1").wait_for_visible()

        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("invocation_step_jobs")

        invocations.step_job_information(order_index="1").wait_for_visible()
        assert (
            "collection_creates_pair"
            in invocations.step_job_information_tool_id(order_index="1").wait_for_visible().text
        )

        # switch to outputs tab
        invocations.step_outputs_tab_link.wait_for_and_click()

        invocations.step_output_collection(order_index="1").wait_for_visible()
        invocations.step_output_collection_toggle(order_index="1").wait_for_and_click()
        invocations.step_output_collection_element_identifier(element_identifier="forward").wait_for_and_click()
        datatype = invocations.step_output_collection_element_datatype(order_index="1").wait_for_text()
        assert datatype == "txt"

    @selenium_test
    @managed_history  # failed job messes with some history wait code we probably shouldn't be using
    def test_invocation_step_jobs_with_failed_jobs(self):
        """Test invocation step jobs view with mixed successful and failed jobs.

        This test verifies:
        - Job state counters (ok and error) display correctly for steps with mixed job states
        - Filtering by failed jobs works correctly
        - Debug tab shows only failed steps
        - Failed steps can be expanded in debug view
        """
        history_id = self.current_history_id()
        self.workflow_populator.run_workflow(
            WORKFLOW_KEEP_SUCCESSFUL_DATASETS,
            test_data=WORKFLOW_KEEP_SUCCESSFUL_DATASETS_TEST_DATA,
            history_id=history_id,
            assert_ok=False,
        )

        # Open the first invocation
        self.invocation_open_latest()

        # Navigate to Steps tab
        invocations = self.components.invocations
        invocations.invocation_tab(label="Steps").wait_for_and_click()

        # Click on a step with multiple mixed failed and successful jobs
        invocations.step_details(order_index="1").wait_for_and_click()
        invocations.step_job_details(order_index="1").wait_for_visible()

        # Verify job state counters
        okay_counter = invocations.step_job_details_state_counter(state="ok").wait_for_visible()
        failed_counter = invocations.step_job_details_state_counter(state="error").wait_for_visible()
        assert okay_counter.get_attribute("data-count") == "1"
        assert failed_counter.get_attribute("data-count") == "1"
        self.screenshot("invocation_steps_view_with_failed_jobs")

        # Filter by failed jobs
        invocations.step_job_details_state_counter(state="error").wait_for_and_click()
        self.screenshot("invocation_steps_view_with_failed_jobs_failed_jobs_list")

        # Navigate to Debug tab
        invocations.invocation_tab(label="Debug").wait_for_and_click()

        # Verify the failed step appears here and the successful step doesn't
        self.screenshot("invocation_steps_view_with_failed_jobs_debug_landing")
        invocations.step_title(order_index=1).wait_for_and_click()
        invocations.step_title(order_index=2).assert_absent()
        self.screenshot("invocation_steps_view_with_failed_jobs_debug_job_expanded")

    def invocation_open_latest(self):
        # TODO: migrate retry_assertion_during_transitions to navigates_galaxy.py so this
        # can be moved there.

        # open invocations panel
        self.home()
        self.components.invocations.activity.wait_for_and_click()

        invocations = self.components.invocations
        invocations.invocations_panel_list.wait_for_visible()

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
        self.components.invocations.activity.wait_for_and_click()

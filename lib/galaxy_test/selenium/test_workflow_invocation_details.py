from galaxy_test.base.workflow_fixtures import WORKFLOW_WITH_OUTPUT_COLLECTION
from .framework import (
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
        gx_selenium_context.navigate_to_invocations()
        invocations = gx_selenium_context.components.invocations
        invocations.invocations_table.wait_for_visible()

        @retry_assertion_during_transitions
        def assert_has_row():
            invocations.invocations_table_rows.wait_for_visible()
            invocation_rows = invocations.invocations_table_rows.all()
            assert len(invocation_rows) > 0
            return invocation_rows[0]

        assert_has_row()

        invocations.state_details.assert_absent()
        invocations.toggle_invocation_details.wait_for_visible()
        details = invocations.toggle_invocation_details.all()[0]
        details.click()
        invocations.state_details.wait_for_visible()

        @retry_assertion_during_transitions
        def assert_progress_steps_note_contains(text):
            assert text in invocations.progress_steps_note.wait_for_visible().text

        assert_progress_steps_note_contains("3 of 3 steps successfully scheduled.")
        assert "2 of 2 jobs complete." in invocations.progress_jobs_note.wait_for_visible().text

        invocations.invocation_tab(label="Inputs").wait_for_and_click()
        invocations.input_details_title(label="text_input").wait_for_visible()
        assert "Test_Dataset" in invocations.input_details_name(label="text_input").wait_for_visible().text

        invocations.invocation_tab(label="Overview").wait_for_and_click()
        invocations.hide_invocation_graph.wait_for_and_click()
        assert "Step 1: text_input" in invocations.step_title(order_index="0").wait_for_visible().text
        assert "Step 2: split_up" in invocations.step_title(order_index="1").wait_for_visible().text
        assert "Step 3: paired" in invocations.step_title(order_index="2").wait_for_visible().text

        invocations.step_details(order_index="1").wait_for_and_click()
        invocations.step_job_details(order_index="1").wait_for_and_click()
        invocations.step_job_table(order_index="1").wait_for_visible()
        invocations.step_job_table_rows(order_index="1").wait_for_visible()
        job_rows = invocations.step_job_table_rows(order_index="1").all()
        assert len(job_rows) == 1

        invocations.step_job_information(order_index="1").assert_absent()
        job_rows[0].click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("invocations_job_table")

        invocations.step_job_information(order_index="1").wait_for_visible()
        assert (
            "collection_creates_pair"
            in invocations.step_job_information_tool_id(order_index="1").wait_for_visible().text
        )

        invocations.step_output_collection(order_index="1").wait_for_and_click()
        invocations.step_output_collection_toggle(order_index="1").wait_for_and_click()
        invocations.step_output_collection_element_identifier(element_identifier="forward").wait_for_and_click()
        datatype = invocations.step_output_collection_element_datatype(order_index="1").wait_for_text()
        assert datatype == "txt"

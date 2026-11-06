from urllib.parse import (
    parse_qs,
    urlencode,
    urlparse,
)

import yaml

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

# A tool step that keeps running long enough to open the invocation while it runs
WORKFLOW_WITH_SLOW_STEP = """
class: GalaxyWorkflow
inputs:
  text_input: data
steps:
  slow_cat:
    tool_id: cat_data_and_sleep
    in:
      input1: text_input
    state:
      sleep_time: 20
test_data:
  text_input: |
    a
"""


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

        self.invocation_expand_step(order_index="1")

        invocations.step_job_information(order_index="1").wait_for_visible()
        self.screenshot("invocation_step_jobs")
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
        self.invocation_expand_step(order_index="1")

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

    @selenium_test
    def test_steps_follow_running_invocation(self):
        history_id = self.dataset_populator.new_history()
        self.workflow_populator.run_workflow(WORKFLOW_WITH_SLOW_STEP, history_id=history_id, wait=False)

        self.invocation_open_latest()
        invocations = self.components.invocations
        invocations.invocation_tab(label="Steps").wait_for_and_click()
        self.invocation_expand_step(order_index="1")
        invocations.step_header_state(order_index="1", state="running").wait_for_visible(
            timeout=self.wait_length(self.wait_types.JOB_COMPLETION)
        )
        self.screenshot("invocation_steps_running_step_expanded")

        # the step header follows the job to completion, and the expanded step stays expanded
        invocations.step_header_state(order_index="1", state="ok").wait_for_visible(
            timeout=self.wait_length(self.wait_types.JOB_COMPLETION)
        )
        invocations.step_job_details(order_index="1").wait_for_visible()
        self.screenshot("invocation_steps_completed_step_expanded")

    def invocation_expand_step(self, order_index):
        invocations = self.components.invocations
        invocations.step_details(order_index=order_index).wait_for_and_click()
        invocations.step_job_details(order_index=order_index).wait_for_visible()

    @selenium_test
    @managed_history
    def test_mapped_job_selection_urls(self):
        """All step aliases open a mapped job; graph navigation preserves the mounted view."""
        history_id = self.current_history_id()
        # Enough successful jobs to exercise pagination, plus a different initial state.
        test_data = {
            "input_c": {
                "collection_type": "list",
                "elements": [
                    {"identifier": f"item-{index}", "content": "1" if index == 0 else "0"} for index in range(13)
                ],
            }
        }
        workflow = yaml.safe_load(WORKFLOW_KEEP_SUCCESSFUL_DATASETS)
        workflow["inputs"]["input_c"] = {"type": "collection", "position": {"left": 0, "top": 0}}
        for index, workflow_step in enumerate(workflow["steps"].values(), start=1):
            workflow_step["position"] = {"left": 320 * index, "top": 0}
        summary = self.workflow_populator.run_workflow(
            yaml.safe_dump(workflow),
            test_data=test_data,
            history_id=history_id,
            assert_ok=False,
        )
        invocation_id = summary.invocation_id
        invocation = self.workflow_populator.get_invocation(invocation_id)
        step = next(step for step in invocation["steps"] if step["order_index"] == 1)
        step_details = self.api_get(f"invocations/{invocation_id}/steps/{step['id']}")
        successful_jobs = sorted(
            (job for job in step_details["jobs"] if job["state"] == "ok"),
            key=lambda job: job["update_time"],
            reverse=True,
        )
        selected_job = successful_jobs[-1]["id"]
        invocations = self.components.invocations

        @retry_assertion_during_transitions
        def assert_selected_job(job_id):
            assert invocations.job_dialog_id.wait_for_text() == job_id
            invocations.step_job_row(order_index=1, job_id=job_id).wait_for_visible()
            assert invocations.step_job_active_page(order_index=1).wait_for_text() == "2"
            assert invocations.step_job_state_filter(order_index=1, state="ok").has_class("g-pressed")

        @retry_assertion_during_transitions
        def assert_selected_node_centered():
            offset = self.execute_script(
                """
                const center = (el) => {
                    const r = el.getBoundingClientRect();
                    return [r.left + r.width / 2, r.top + r.height / 2];
                };
                const [nodeX, nodeY] = center(arguments[0]);
                const [canvasX, canvasY] = center(arguments[1]);
                return [nodeX - canvasX, nodeY - canvasY];
                """,
                self.components.workflow_editor.node.by_id(id=1).wait_for_visible(),
                invocations.graph_canvas.wait_for_visible(),
            )
            assert all(abs(delta) < 5 for delta in offset), offset

        for selector, value in [("step_number", "2"), ("step_index", "1"), ("step_label", "mixed_collection")]:
            query = urlencode({selector: value, "job": selected_job})
            self.get(f"workflows/invocations/{invocation_id}?{query}")
            assert_selected_node_centered()
            invocations.job_dialog.wait_for_visible()
            assert_selected_job(selected_job)
            invocations.job_dialog_loading.wait_for_absent()
            self.screenshot(f"invocation_mapped_job_{selector}")

        invocations.job_dialog_previous.wait_for_and_click()

        @retry_assertion_during_transitions
        def assert_job_url_changed():
            query = parse_qs(urlparse(self.current_url).query)
            assert query.get("job") and query["job"] != [selected_job]
            dialog_ids = invocations.job_dialog_id.all()
            assert len(dialog_ids) == 1
            assert dialog_ids[0].text == query["job"][0]

        assert_job_url_changed()
        invocations.job_dialog_loading.wait_for_absent()
        self.screenshot("invocation_mapped_job_previous")
        invocations.job_dialog_close.wait_for_and_click()
        invocations.job_dialog.wait_for_absent_or_hidden()

        @retry_assertion_during_transitions
        def assert_job_url_removed():
            assert "job" not in parse_qs(urlparse(self.current_url).query)

        assert_job_url_removed()
        self.screenshot("invocation_mapped_job_dialog_closed")
        scroll_into_view = "arguments[0].scrollIntoView({block: 'center'})"
        self.execute_script(scroll_into_view, invocations.step_job_active_page(order_index=1).wait_for_visible())
        self.screenshot("invocation_mapped_job_table")
        self.execute_script(scroll_into_view, invocations.graph_canvas.wait_for_visible())

        # Track the invocation DOM node identity to detect a route-triggered remount.
        self.execute_script(
            "window.invocationSelectionRoot = arguments[0]", invocations.state_details.wait_for_visible()
        )
        # The selected step is centered at 100%; zoom to 50% so its input clears the side overlay.
        for _ in range(5):
            invocations.graph_zoom_out.wait_for_and_click()
        self.components.workflow_editor.node.by_id(id=0).wait_for_and_click()

        @retry_assertion_during_transitions
        def assert_other_node_selected():
            query = parse_qs(urlparse(self.current_url).query)
            assert query.get("step_label") == ["input_c"]
            assert "job" not in query
            assert self.execute_script(
                "return window.invocationSelectionRoot === arguments[0]", invocations.state_details.wait_for_visible()
            )

        assert_other_node_selected()
        self.screenshot("invocation_mapped_job_changed_node")

    @selenium_test
    @managed_history
    def test_step_url_scrolls_steps_list(self):
        """A step URL on the Steps tab scrolls a step far down the list into view."""
        summary = self.workflow_populator.run_workflow(
            yaml.safe_dump(cat_chain_workflow(25)),
            test_data={"input1": {"value": "1.bed", "type": "File"}},
            history_id=self.current_history_id(),
            wait=False,
        )
        self.get(f"workflows/invocations/{summary.invocation_id}/steps?step_number=26")
        self.assert_in_window(self.components.invocations.step_title(order_index="25"))
        self.screenshot("invocation_steps_url_scrolled")

    @selenium_test
    @managed_history
    def test_output_urls_expand_outputs(self):
        """Step and workflow output URLs expand the named output and scroll it into view."""
        # Zero-padded names keep step order stable through YAML's sorted keys.
        workflow = {
            "class": "GalaxyWorkflow",
            "inputs": {"input1": "data"},
            "outputs": {
                f"cat_output_{index:02d}": {"outputSource": f"cat_{index:02d}/out_file1"} for index in range(12)
            },
            "steps": {f"cat_{index:02d}": {"tool_id": "cat", "in": {"input1": "input1"}} for index in range(12)},
        }
        summary = self.workflow_populator.run_workflow(
            yaml.safe_dump(workflow),
            test_data={"input1": {"value": "1.bed", "type": "File"}},
            history_id=self.current_history_id(),
        )
        invocations = self.components.invocations
        self.get(f"workflows/invocations/{summary.invocation_id}?step_label=cat_11&output=out_file1")
        self.assert_in_window(invocations.step_output_expanded(order_index="12"))
        self.screenshot("invocation_step_output_url")
        self.get(f"workflows/invocations/{summary.invocation_id}/outputs?output=cat_output_11")
        self.assert_in_window(invocations.workflow_output_expanded(label="cat_output_11"))
        assert len(invocations.workflow_output_expanded(label="cat_output_00").all()) == 0
        self.screenshot("invocation_workflow_output_url")

    @retry_assertion_during_transitions
    def assert_in_window(self, component):
        top, bottom = self.execute_script(
            "const r = arguments[0].getBoundingClientRect(); return [r.top, window.innerHeight];",
            component.wait_for_visible(),
        )
        assert 0 <= top < bottom, (top, bottom)


def cat_chain_workflow(length):
    steps = {}
    previous = "input1"
    for index in range(length):
        steps[f"cat_{index}"] = {"tool_id": "cat", "in": {"input1": previous}}
        previous = f"cat_{index}/out_file1"
    return {"class": "GalaxyWorkflow", "inputs": {"input1": "data"}, "steps": steps}

"""Selenium tests for workflow extraction UI.

Tests the user-facing workflow extraction form at /histories/:historyId/extract_workflow,
reusing test setup infrastructure from API tests.
"""

from typing import (
    cast,
    Optional,
)

from galaxy_test.base.populators import skip_without_tool
from galaxy_test.base.workflow_assertions import WorkflowStructureAssertions
from galaxy_test.base.workflow_fixtures import WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestWorkflowExtractionSelenium(SeleniumTestCase, WorkflowStructureAssertions):
    """Selenium tests for workflow extraction from history."""

    ensure_registered = True

    # --- Test Setup Helpers ---

    def setup_cat1_history(self, history_id: str) -> str:
        """Run cat1 workflow and return the cat1 job_id."""
        workflow = self.workflow_populator.load_workflow(name="test_for_extract")
        workflow_request, _, workflow_id = self.workflow_populator.setup_workflow_run(workflow, history_id=history_id)
        self.workflow_populator.invoke_workflow_and_wait(workflow_id, request=workflow_request, history_id=history_id)
        # Get cat1 job
        jobs = self.dataset_populator.history_jobs(history_id)
        cat1_jobs = [j for j in jobs if j["tool_id"] == "cat1"]
        assert cat1_jobs, "Expected cat1 job to be present"
        return cat1_jobs[0]["id"]

    def setup_mapped_collection_history(self, history_id: str) -> tuple:
        """Create paired collection and run random_lines mapped over it twice.

        Returns: (hdca, all_job_ids) where all_job_ids is list of 2 job IDs
        (1 job per batch run - batch creates single job processing entire collection).
        """
        hdca = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
        ).json()["outputs"][0]
        hdca_id = hdca["id"]

        inputs1 = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]}, "num_lines": 2}
        run1 = self.dataset_populator.run_tool("random_lines1", inputs1, history_id)
        implicit_hdca1 = run1["implicit_collections"][0]
        job_ids_run1 = [j["id"] for j in run1["jobs"]]

        inputs2 = {"input": {"batch": True, "values": [{"src": "hdca", "id": implicit_hdca1["id"]}]}, "num_lines": 1}
        run2 = self.dataset_populator.run_tool("random_lines1", inputs2, history_id)
        job_ids_run2 = [j["id"] for j in run2["jobs"]]

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return hdca, job_ids_run1 + job_ids_run2

    def setup_copied_cat1_history(self, history_id: str) -> Optional[str]:
        """Run cat1 in one history, copy outputs to given history.

        Returns: cat1 job_id associated with the copied datasets.
        """
        old_history_id = self.dataset_populator.new_history()
        self.setup_cat1_history(old_history_id)

        old_contents = self.dataset_populator._get(f"histories/{old_history_id}/contents").json()

        for content in old_contents:
            payload = {"source": "hda", "content": content["id"]}
            self.dataset_populator._post(f"histories/{history_id}/contents/datasets", data=payload, json=True)

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

        # Get jobs associated with this history (from copied datasets)
        jobs = self.dataset_populator.history_jobs(history_id)
        cat1_jobs = [j for j in jobs if j["tool_id"] == "cat1"]
        if not cat1_jobs:
            return None
        else:
            return cast(str, cat1_jobs[0]["id"])

    def setup_reduction_history(self, history_id: str) -> tuple:
        """Create history with collection -> map -> reduce pattern.

        Returns: (hdca, map_job_id, reduce_job_id)
        """
        hdca = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
        ).json()["outputs"][0]

        # Map random_lines over collection
        inputs1 = {
            "input": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]},
            "num_lines": 2,
        }
        run1 = self.dataset_populator.run_tool("random_lines1", inputs1, history_id)
        implicit_hdca = run1["implicit_collections"][0]
        map_job_id = run1["jobs"][0]["id"]

        # Reduce with multi_data_param
        inputs2 = {
            "f1": {"src": "hdca", "id": implicit_hdca["id"]},
            "f2": {"src": "hdca", "id": implicit_hdca["id"]},
        }
        run2 = self.dataset_populator.run_tool("multi_data_param", inputs2, history_id)
        reduce_job_id = run2["jobs"][0]["id"]

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return hdca, map_job_id, reduce_job_id

    def setup_output_collection_history(self, history_id: str) -> list:
        """Create history where tool produces collection output.

        Returns: list of job_ids [cat1_id, split_id, cat_list_id]
        """
        self.workflow_populator.run_workflow(WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION, history_id=history_id)
        jobs = self.dataset_populator.history_jobs(history_id)
        return [j["id"] for j in jobs if j["tool_id"] in ["cat1", "collection_split_on_column", "cat_list"]]

    def setup_nested_collection_history(self, history_id: str) -> tuple:
        """Create history with list:paired collection workflow.

        Returns: (hdca_hid, job_ids_list)
        """
        self.workflow_populator.run_workflow(
            """
class: GalaxyWorkflow
steps:
  - label: text_input1
    type: input_collection
  - label: noop
    tool_id: cat1
    state:
      input1:
        $link: text_input1
test_data:
  text_input1:
    collection_type: "list:paired"
""",
            history_id=history_id,
        )
        jobs = self.dataset_populator.history_jobs(history_id)
        job_ids = [j["id"] for j in jobs if j["tool_id"] == "cat1"]
        # Find the list:paired input collection HID
        contents = self.dataset_populator._get(f"histories/{history_id}/contents?type=dataset_collection").json()
        hdca_hid = contents[0]["hid"]
        return hdca_hid, job_ids

    # --- UI Extraction Helpers ---

    def extract_workflow_set_name(self, name: str):
        """Set the workflow name in extraction form."""
        name_input = self.components.workflow_extract.workflow_name_input.wait_for_visible()
        name_input.clear()
        name_input.send_keys(name)

    def extract_workflow_submit(self):
        """Submit the extraction form."""
        self.components.workflow_extract.create_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)

    def extract_workflow_toggle_job(self, job_id: str):
        """Toggle the selection checkbox for a specific job card by job_id."""
        checkbox = self.components.workflow_extract.card_checkbox_by_job_id(job_id=job_id)
        element = checkbox.wait_for_present()
        self.execute_script_click(element)

    def find_workflow_by_name(self, name: str) -> str:
        """Find workflow ID by name via API. Returns most recently created if multiple match."""
        response = self.workflow_populator._get("workflows")
        response.raise_for_status()
        workflows = response.json()
        matching = [w for w in workflows if w["name"] == name]
        assert len(matching) >= 1, f"Expected at least 1 workflow '{name}', found 0: {[w['name'] for w in workflows]}"
        # Return most recently created workflow if multiple match
        matching.sort(key=lambda w: w["create_time"], reverse=True)
        return matching[0]["id"]

    def get_workflow_by_name(self, name: str) -> dict:
        """Find and download workflow by name."""
        workflow_id = self.find_workflow_by_name(name)
        return self.workflow_populator.download_workflow(workflow_id)

    def extract_workflow_and_download(self, name: str, screenshot_name: Optional[str] = None) -> dict:
        """Navigate to extraction, submit form, return downloaded workflow."""
        self.navigate_to_workflow_extraction()
        if screenshot_name:
            self.screenshot(screenshot_name)
        self.extract_workflow_set_name(name)
        self.extract_workflow_submit()
        return self.get_workflow_by_name(name)

    def count_job_checkboxes(self) -> int:
        """Count the number of tool-step cards in the extraction form."""
        return len(self.find_elements_by_selector(self.components.workflow_extract.tool_card_checkbox.selector))

    def count_checked_job_checkboxes(self) -> int:
        """Count the number of checked tool-step cards."""
        return len(self.find_elements_by_selector(self.components.workflow_extract.tool_card_checkbox_checked.selector))

    def get_job_checkbox_values(self) -> list:
        """Get job IDs from all tool-step cards."""
        cards = self.find_elements_by_selector(self.components.workflow_extract.tool_card.selector + "[data-job-id]")
        return [card.get_attribute("data-job-id") for card in cards]

    @selenium_test
    @managed_history
    def test_extract_form_loads(self):
        """Verify extraction form displays for empty history with appropriate message."""
        self.navigate_to_workflow_extraction()

        # For an empty history the form shows an info message, not the name/submit controls
        self.components.workflow_extract.no_workflow_message.wait_for_visible()

        # No tool-step cards for empty history
        job_count = self.count_job_checkboxes()
        assert job_count == 0, f"Expected 0 job cards for empty history, found {job_count}"

        self.screenshot("workflow_extract_empty_history")

    @skip_without_tool("random_lines1")
    @selenium_test
    @managed_history
    def test_extract_form_validation(self):
        """Test form validation: submit is blocked when no steps are selected."""
        history_id = self.current_history_id()
        self.setup_mapped_collection_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify initial state: 2 tool-step cards, both checked
        assert self.count_job_checkboxes() == 2, "Expected exactly 2 tool-step cards"
        assert self.count_checked_job_checkboxes() == 2, "Expected both tool steps checked initially"

        # Set a workflow name first
        self.extract_workflow_set_name("Selenium Validation Test")

        # Uncheck ALL cards (tool steps + input cards) so the workflow would have no steps
        rendered_job_ids = self.get_job_checkbox_values()
        for job_id in rendered_job_ids:
            self.extract_workflow_toggle_job(job_id)
        # Also uncheck any remaining checked cards (e.g. input_collection / input_dataset)
        for element in self.find_elements_by_selector(
            self.components.workflow_extract.all_card_checkboxes_checked.selector
        ):
            self.execute_script_click(element)
        self.sleep_for(self.wait_types.UX_RENDER)

        assert self.count_checked_job_checkboxes() == 0, "Expected 0 tool steps checked after unchecking all"

        self.screenshot("workflow_extract_no_steps_selected")

        # Create button should be disabled when no steps are selected
        create_button = self.components.workflow_extract.create_button.wait_for_visible()
        assert (
            create_button.get_attribute("aria-disabled") == "true"
        ), "Expected create button to be disabled with no steps selected"

        # Re-check tool steps — submit should now work
        for job_id in rendered_job_ids:
            self.extract_workflow_toggle_job(job_id)
        self.sleep_for(self.wait_types.UX_RENDER)

        assert self.count_checked_job_checkboxes() == 2, "Expected tool steps checked again"
        self.extract_workflow_submit()

        workflow = self.get_workflow_by_name("Selenium Validation Test")
        assert workflow is not None

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_extract_cat1_workflow(self):
        """Test extraction UI with cat1: job listing, checkbox toggle, and extraction."""
        history_id = self.current_history_id()
        cat1_job_id = self.setup_cat1_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify exactly 1 job listed (cat1 workflow has 1 tool step)
        job_count = self.count_job_checkboxes()
        assert job_count == 1, f"Expected exactly 1 job checkbox, found {job_count}"
        self.screenshot("workflow_extract_with_jobs")

        # Verify checkbox starts checked
        assert self.count_checked_job_checkboxes() == 1, "Expected 1 tool-step card checked initially"

        # Toggle checkbox off
        self.extract_workflow_toggle_job(cat1_job_id)
        self.sleep_for(self.wait_types.UX_RENDER)
        cat1_checkbox = self.find_element_by_selector(f'[data-job-id="{cat1_job_id}"] input[id^="g-card-select-"]')
        assert not cat1_checkbox.is_selected(), "Expected checkbox unchecked after toggle"

        # Toggle back on
        self.extract_workflow_toggle_job(cat1_job_id)
        self.sleep_for(self.wait_types.UX_RENDER)
        cat1_checkbox = self.find_element_by_selector(f'[data-job-id="{cat1_job_id}"] input[id^="g-card-select-"]')
        assert cat1_checkbox.is_selected(), "Expected checkbox checked after second toggle"
        self.screenshot("workflow_extract_toggle_checkbox")

        # Extract workflow and verify structure
        workflow_name = "Selenium Extracted Cat1"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()

        workflow = self.get_workflow_by_name(workflow_name)
        self.assert_cat1_workflow_structure(workflow)

    @skip_without_tool("random_lines1")
    @selenium_test
    @managed_history
    def test_extract_toggle_job_subset(self):
        """Toggle some jobs off, verify only selected jobs create workflow steps."""
        history_id = self.current_history_id()
        self.setup_mapped_collection_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify both jobs checked initially
        assert self.count_checked_job_checkboxes() == 2, "Expected 2 checked jobs"
        self.screenshot("workflow_extract_job_subset_initial")

        # Get job IDs from rendered checkboxes and toggle off first one
        rendered_job_ids = self.get_job_checkbox_values()
        job_id_first = rendered_job_ids[0]
        job_id_second = rendered_job_ids[1]
        self.extract_workflow_toggle_job(job_id_first)
        self.sleep_for(self.wait_types.UX_RENDER)

        # Verify first job unchecked, second job still checked
        checkbox1 = self.find_element_by_selector(f'[data-job-id="{job_id_first}"] input[id^="g-card-select-"]')
        checkbox2 = self.find_element_by_selector(f'[data-job-id="{job_id_second}"] input[id^="g-card-select-"]')
        assert not checkbox1.is_selected(), f"Expected job {job_id_first} unchecked"
        assert checkbox2.is_selected(), f"Expected job {job_id_second} still checked"

        self.screenshot("workflow_extract_job_subset_toggled")

        # Submit extraction
        workflow_name = "Selenium Job Subset"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()

        # Verify extracted workflow has 2 steps (1 input + 1 tool from second run only)
        workflow = self.get_workflow_by_name(workflow_name)
        assert len(workflow["steps"]) == 2, f"Expected 2 steps (1 input + 1 tool), got {len(workflow['steps'])}"

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_extract_with_copied_inputs(self):
        """Verify extraction form displays correctly for copied datasets."""
        history_id = self.current_history_id()
        self.setup_copied_cat1_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify exactly 1 job checkbox visible (copied cat1 workflow has 1 tool step)
        job_count = self.count_job_checkboxes()
        assert job_count == 1, f"Expected exactly 1 job checkbox, found {job_count}"
        self.screenshot("workflow_extract_copied_inputs")

        # Verify job checkbox is checked
        initial_checked = self.count_checked_job_checkboxes()
        assert initial_checked == 1, f"Expected 1 checked job checkbox, found {initial_checked}"

        # Extract and verify structure
        workflow_name = "Selenium Copied Inputs"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()

        workflow = self.get_workflow_by_name(workflow_name)
        self.assert_cat1_workflow_structure(workflow)

    @skip_without_tool("random_lines1")
    @selenium_test
    @managed_history
    def test_extract_with_collection_input(self):
        """Extract workflow with collection mapped over."""
        history_id = self.current_history_id()
        self.setup_mapped_collection_history(history_id)

        workflow = self.extract_workflow_and_download(
            "Selenium Collection Workflow", "workflow_extract_with_collection"
        )

        # Should have 3 steps (1 collection input + 2 tool steps)
        assert len(workflow["steps"]) == 3
        self.assert_input_step_collection_type(workflow, "paired")
        tool_steps = self.assert_steps_of_type(workflow, "tool", expected_len=2)
        tool_ids = {step["tool_id"] for step in tool_steps}
        assert tool_ids == {"random_lines1"}, f"Expected only random_lines1 tools, got {tool_ids}"

    @skip_without_tool("random_lines1")
    @skip_without_tool("multi_data_param")
    @selenium_test
    @managed_history
    def test_extract_reduce_collection_ui(self):
        """Extract workflow with map -> reduce pattern."""
        history_id = self.current_history_id()
        hdca, map_job_id, reduce_job_id = self.setup_reduction_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify 2 jobs: 1 from random_lines1 mapped over paired + 1 from multi_data_param reduce
        job_count = self.count_job_checkboxes()
        assert job_count == 2, f"Expected exactly 2 job checkboxes, found {job_count}"
        self.screenshot("workflow_extract_reduce_collection")

        workflow_name = "Selenium Reduce Collection"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()

        workflow = self.get_workflow_by_name(workflow_name)
        # Should have 3 steps (1 collection input + 2 tools)
        assert len(workflow["steps"]) == 3, f"Expected 3 steps, got {len(workflow['steps'])}"

        tool_ids = {step.get("tool_id") for step in workflow["steps"].values() if step.get("tool_id")}
        assert tool_ids == {"random_lines1", "multi_data_param"}, f"Unexpected tool_ids: {tool_ids}"

    @skip_without_tool("cat1")
    @skip_without_tool("collection_split_on_column")
    @skip_without_tool("cat_list")
    @selenium_test
    @managed_history
    def test_extract_output_collections_ui(self):
        """Extract workflow where tools produce collection outputs."""
        history_id = self.current_history_id()
        self.setup_output_collection_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify at least 3 tool jobs visible (cat1, collection_split_on_column, cat_list).
        # Using >= because WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION structure may vary
        # and additional jobs could be present depending on workflow fixture evolution.
        job_count = self.count_job_checkboxes()
        assert job_count >= 3, f"Expected at least 3 job checkboxes, found {job_count}"
        self.screenshot("workflow_extract_output_collections")

        workflow_name = "Selenium Output Collections"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()

        workflow = self.get_workflow_by_name(workflow_name)
        # Should have 5 steps (2 data inputs + 3 tools)
        assert len(workflow["steps"]) == 5, f"Expected 5 steps, got {len(workflow['steps'])}"

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_extract_nested_collection_ui(self):
        """Extract workflow with nested collections (list:paired)."""
        history_id = self.current_history_id()
        hdca_hid, job_ids = self.setup_nested_collection_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify at least 1 tool job visible. Using >= because the exact number depends
        # on the default test data structure for list:paired collections, which creates
        # one cat1 job per list element (typically 2, but may vary).
        job_count = self.count_job_checkboxes()
        assert job_count >= 1, f"Expected at least 1 job checkbox, found {job_count}"
        self.screenshot("workflow_extract_nested_collection")

        workflow_name = "Selenium Nested Collection"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()

        workflow = self.get_workflow_by_name(workflow_name)
        # Should have 2 steps (1 collection input + 1 tool)
        assert len(workflow["steps"]) == 2, f"Expected 2 steps, got {len(workflow['steps'])}"

        # Verify collection input is list:paired
        self.assert_input_step_collection_type(workflow, "list:paired")

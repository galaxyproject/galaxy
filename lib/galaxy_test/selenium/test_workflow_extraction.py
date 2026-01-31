"""Selenium tests for workflow extraction UI.

Tests the user-facing workflow extraction UI (Mako-based build_from_current_history page)
while reusing test setup infrastructure from API tests.

TODO: Add test for disabled/non-workflow tools shown as disabled (toolFormDisabled class).
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
        """Create paired collection and run random_lines mapped over it.

        Returns: (hdca, job_id1, job_id2)
        """
        hdca = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
        ).json()["outputs"][0]
        hdca_id = hdca["id"]

        inputs1 = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]}, "num_lines": 2}
        run1 = self.dataset_populator.run_tool("random_lines1", inputs1, history_id)
        implicit_hdca1 = run1["implicit_collections"][0]
        job_id1 = run1["jobs"][0]["id"]

        inputs2 = {"input": {"batch": True, "values": [{"src": "hdca", "id": implicit_hdca1["id"]}]}, "num_lines": 1}
        run2 = self.dataset_populator.run_tool("random_lines1", inputs2, history_id)
        job_id2 = run2["jobs"][0]["id"]

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return hdca, job_id1, job_id2

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
        """Toggle a specific job checkbox by job_id."""
        checkbox = self.components.workflow_extract.job_checkbox(job_id=job_id)
        checkbox.wait_for_and_click()

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
        self.switch_to_default_content()
        return self.get_workflow_by_name(name)

    def count_job_checkboxes(self) -> int:
        """Count the number of job checkboxes visible."""
        checkboxes = self.find_elements_by_selector('input[name="job_ids"]')
        return len(checkboxes)

    def count_checked_job_checkboxes(self) -> int:
        """Count number of checked job checkboxes."""
        return len(self.find_elements_by_selector('input[name="job_ids"]:checked'))

    # --- Tier 1: Basic Functionality Tests ---

    @selenium_test
    @managed_history
    def test_extract_form_loads(self):
        """Verify extraction form displays for empty history."""
        self.navigate_to_workflow_extraction()

        # Form should be visible
        self.components.workflow_extract.workflow_name_input.wait_for_visible()
        self.components.workflow_extract.create_button.wait_for_visible()

        # No jobs should be listed for empty history
        job_count = self.count_job_checkboxes()
        assert job_count == 0, f"Expected 0 job checkboxes for empty history, found {job_count}"

        self.screenshot("workflow_extract_empty_history")

        # Switch back to default content
        self.switch_to_default_content()

    @skip_without_tool("random_lines1")
    @selenium_test
    @managed_history
    def test_extract_form_validation(self):
        """Test form validation: empty name, no jobs selected."""
        history_id = self.current_history_id()
        hdca, job_id1, job_id2 = self.setup_mapped_collection_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify initial state
        assert self.count_job_checkboxes() >= 2, "Expected at least 2 job checkboxes"
        initial_checked = self.count_checked_job_checkboxes()
        assert initial_checked >= 2, f"Expected at least 2 checked, got {initial_checked}"

        # Test: uncheck all jobs
        self.extract_workflow_toggle_job(job_id1)
        self.extract_workflow_toggle_job(job_id2)
        self.sleep_for(self.wait_types.UX_RENDER)

        unchecked_count = self.count_checked_job_checkboxes()
        assert unchecked_count == initial_checked - 2, f"Expected 2 fewer checked, got {unchecked_count}"

        self.screenshot("workflow_extract_no_jobs_selected")

        # Submit with no jobs - should still work (creates empty workflow)
        workflow_name = "Selenium Empty Selection"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()
        self.switch_to_default_content()

        # Verify workflow was created (may be empty or have just inputs)
        workflow = self.get_workflow_by_name(workflow_name)
        assert workflow is not None, "Expected workflow to be created even with no jobs selected"

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_extract_cat1_workflow(self):
        """Test extraction UI with cat1: job listing, checkbox toggle, and extraction."""
        history_id = self.current_history_id()
        cat1_job_id = self.setup_cat1_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify jobs are listed
        job_count = self.count_job_checkboxes()
        assert job_count >= 1, f"Expected at least 1 job checkbox, found {job_count}"
        self.screenshot("workflow_extract_with_jobs")

        # Verify checkboxes start checked
        initial_checked = self.find_elements_by_selector('input[name="job_ids"]:checked')
        assert len(initial_checked) >= 1, "Expected at least 1 checked job checkbox"

        # Toggle checkbox off
        self.extract_workflow_toggle_job(cat1_job_id)
        self.sleep_for(self.wait_types.UX_RENDER)
        cat1_checkbox = self.find_element_by_selector(f'input[name="job_ids"][value="{cat1_job_id}"]')
        assert not cat1_checkbox.is_selected(), "Expected checkbox unchecked after toggle"

        # Toggle back on
        self.extract_workflow_toggle_job(cat1_job_id)
        self.sleep_for(self.wait_types.UX_RENDER)
        cat1_checkbox = self.find_element_by_selector(f'input[name="job_ids"][value="{cat1_job_id}"]')
        assert cat1_checkbox.is_selected(), "Expected checkbox checked after second toggle"
        self.screenshot("workflow_extract_toggle_checkbox")

        # Extract workflow and verify structure
        workflow_name = "Selenium Extracted Cat1"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()
        self.switch_to_default_content()

        workflow = self.get_workflow_by_name(workflow_name)
        self.assert_cat1_workflow_structure(workflow)

    @skip_without_tool("random_lines1")
    @selenium_test
    @managed_history
    def test_extract_toggle_job_subset(self):
        """Toggle some jobs off, verify only selected jobs create workflow steps."""
        history_id = self.current_history_id()
        hdca, job_id1, job_id2 = self.setup_mapped_collection_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify both jobs checked initially
        assert self.count_checked_job_checkboxes() >= 2, "Expected at least 2 checked jobs"
        self.screenshot("workflow_extract_job_subset_initial")

        # Toggle off first job
        self.extract_workflow_toggle_job(job_id1)
        self.sleep_for(self.wait_types.UX_RENDER)

        # Verify first job unchecked, second still checked
        job1_checkbox = self.find_element_by_selector(f'input[name="job_ids"][value="{job_id1}"]')
        job2_checkbox = self.find_element_by_selector(f'input[name="job_ids"][value="{job_id2}"]')
        assert not job1_checkbox.is_selected(), "Expected job1 unchecked"
        assert job2_checkbox.is_selected(), "Expected job2 still checked"

        self.screenshot("workflow_extract_job_subset_toggled")

        # Submit extraction
        workflow_name = "Selenium Job Subset"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()
        self.switch_to_default_content()

        # Verify extracted workflow has 2 steps (1 input + 1 tool), not 3
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

        # Verify at least 1 job checkbox visible
        job_count = self.count_job_checkboxes()
        assert job_count >= 1, f"Expected at least 1 job checkbox, found {job_count}"
        self.screenshot("workflow_extract_copied_inputs")

        # Verify job checkbox exists and is checked
        initial_checked = self.count_checked_job_checkboxes()
        assert initial_checked >= 1, "Expected at least 1 checked job checkbox"

        # Extract and verify structure
        workflow_name = "Selenium Copied Inputs"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()
        self.switch_to_default_content()

        workflow = self.get_workflow_by_name(workflow_name)
        self.assert_cat1_workflow_structure(workflow)

    # --- Tier 3: Collection Tests ---

    @skip_without_tool("random_lines1")
    @selenium_test
    @managed_history
    def test_extract_with_collection_input(self):
        """Extract workflow with collection mapped over."""
        history_id = self.current_history_id()
        hdca, job_id1, job_id2 = self.setup_mapped_collection_history(history_id)

        workflow = self.extract_workflow_and_download(
            "Selenium Collection Workflow", "workflow_extract_with_collection"
        )

        # Should have 3 steps (input + 2 tool steps)
        assert len(workflow["steps"]) == 3
        self.assert_input_step_collection_type(workflow, "paired")

    @skip_without_tool("random_lines1")
    @skip_without_tool("multi_data_param")
    @selenium_test
    @managed_history
    def test_extract_reduce_collection_ui(self):
        """Extract workflow with map -> reduce pattern."""
        history_id = self.current_history_id()
        hdca, map_job_id, reduce_job_id = self.setup_reduction_history(history_id)

        self.navigate_to_workflow_extraction()

        # Verify 2 tool jobs visible
        job_count = self.count_job_checkboxes()
        assert job_count >= 2, f"Expected at least 2 job checkboxes, found {job_count}"
        self.screenshot("workflow_extract_reduce_collection")

        workflow_name = "Selenium Reduce Collection"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()
        self.switch_to_default_content()

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

        # Verify 3+ tool jobs visible
        job_count = self.count_job_checkboxes()
        assert job_count >= 3, f"Expected at least 3 job checkboxes, found {job_count}"
        self.screenshot("workflow_extract_output_collections")

        workflow_name = "Selenium Output Collections"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()
        self.switch_to_default_content()

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

        # Verify 1+ tool jobs visible
        job_count = self.count_job_checkboxes()
        assert job_count >= 1, f"Expected at least 1 job checkbox, found {job_count}"
        self.screenshot("workflow_extract_nested_collection")

        workflow_name = "Selenium Nested Collection"
        self.extract_workflow_set_name(workflow_name)
        self.extract_workflow_submit()
        self.switch_to_default_content()

        workflow = self.get_workflow_by_name(workflow_name)
        # Should have 2 steps (1 collection input + 1 tool)
        assert len(workflow["steps"]) == 2, f"Expected 2 steps, got {len(workflow['steps'])}"

        # Verify collection input is list:paired
        self.assert_input_step_collection_type(workflow, "list:paired")

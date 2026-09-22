"""Selenium tests for workflow run input selection and filtering."""

from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)

INPUT_LABEL = "input1"


class TestWorkflowRunInputs(SeleniumTestCase):
    """Tests for workflow run input collection filtering."""

    ensure_registered = True

    @selenium_test
    @managed_history
    def test_sample_sheet_from_existing_filters_on_collection_type(self):
        """Verify collection selection dialog only shows compatible types."""
        workflow_run = self.components.workflow_run
        sample_sheet = workflow_run.input.sample_sheet

        # 1. Create fixtures - for each test one that matches the filter and one that does.
        history_id = self.current_history_id()
        flat_list_id = self.dataset_collection_populator.create_list_in_history(
            history_id, name="flat_list", wait=True
        ).json()["output_collections"][0]["id"]
        paired_list_id = self.dataset_collection_populator.create_list_of_pairs_in_history(
            history_id, name="paired_list", wait=True
        ).json()["output_collections"][0]["id"]

        # 2. Navigate home to see complete collections
        self.home()

        # 3. Setup workflow with sample_sheet:paired input
        id = self._setup_sample_sheet_paired_workflow()
        self.workflow_run_with_id(id)
        self._open_collection_selection_dialog()

        # 5. Assert compatible collection IS present
        sample_sheet.collection_selection(id=paired_list_id).wait_for_present()

        # 6. Assert incompatible collection is NOT present
        sample_sheet.collection_selection(id=flat_list_id).assert_absent()

        # 7. Repeat with inverted checks for flat sample_sheet
        id = self._setup_sample_sheet_flat_workflow()
        self.workflow_run_with_id(id)
        self._open_collection_selection_dialog()
        sample_sheet.collection_selection(id=flat_list_id).wait_for_present()
        sample_sheet.collection_selection(id=paired_list_id).assert_absent()

    def _open_collection_selection_dialog(self):
        """Open collection selection dialog for given input."""
        workflow_run = self.components.workflow_run
        input = workflow_run.input._(label=INPUT_LABEL)
        input.upload.wait_for_and_click()
        sample_sheet = workflow_run.input.sample_sheet
        sample_sheet._.wait_for_present()
        sample_sheet.data_import_source_from(source="collection").wait_for_and_click()
        sample_sheet.wizard_next_button.wait_for_and_click()
        return sample_sheet

    def _setup_sample_sheet_paired_workflow(self):
        """Create minimal workflow with sample_sheet:paired input."""
        return self._setup_single_input_workflow(collection_type="sample_sheet:paired")

    def _setup_sample_sheet_flat_workflow(self):
        """Create minimal workflow with sample_sheet (flat) input."""
        return self._setup_single_input_workflow(collection_type="sample_sheet")

    def _setup_single_input_workflow(self, collection_type: str):
        workflow_content = f"""
class: GalaxyWorkflow
inputs:
    {INPUT_LABEL}:
        type: collection
        collection_type: {collection_type}
steps: []
"""
        workflow_id = self.workflow_populator.upload_yaml_workflow(workflow_content)
        return workflow_id

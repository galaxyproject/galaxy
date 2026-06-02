"""Selenium tests for extracting a workflow from a notebook (history-attached page).

A notebook's history_dataset_display directives name the outputs the user cares
about. Reaching the extraction form from the notebook (the ``from_page`` path)
should pre-check only the producing subgraph of those referenced outputs and
pre-star the referenced outputs — unlike the history-options path, which checks
the whole history. These tests drive that wiring end to end against a live server.
"""

from galaxy_test.base.populators import skip_without_tool
from galaxy_test.base.workflow_assertions import WorkflowStructureAssertions
from .framework import (
    ExtractsWorkflows,
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestNotebookWorkflowExtraction(SeleniumTestCase, ExtractsWorkflows, WorkflowStructureAssertions):
    """Selenium tests for the notebook → workflow extraction entry point."""

    ensure_registered = True

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_notebook_seeds_referenced_subgraph(self):
        """Notebook referencing one of two independent runs seeds only that subgraph.

        Two independent cat1 runs share a history; the notebook references only
        run A's output. Opening the form via the toolbar must pre-check run A's
        card (and its inputs) while leaving run B unchecked, pre-star run A's
        output, and extract a workflow containing run A's step only.
        """
        history_id = self.current_history_id()
        job_a, output_a, job_b = self.setup_two_independent_cat1_runs(history_id)
        page = self.dataset_populator.new_notebook_referencing(history_id, [output_a])

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.notebook_click_extract_workflow()
        self.screenshot("notebook_extract_seeded_form")

        # Both tool cards render, but only the referenced run is pre-checked.
        # (If the from_page path were ignored, the form's default would check
        # both — so this count is the regression lever for the whole feature.)
        assert self.count_job_checkboxes() == 2, "Expected both cat1 tool cards to render"
        assert self.count_checked_job_checkboxes() == 1, "Expected only the referenced run pre-checked"

        checkbox_a = self.components.workflow_extract.card_checkbox_by_job_id(job_id=job_a).wait_for_present()
        checkbox_b = self.components.workflow_extract.card_checkbox_by_job_id(job_id=job_b).wait_for_present()
        assert checkbox_a.is_selected(), f"Expected referenced run {job_a} pre-checked"
        assert not checkbox_b.is_selected(), f"Expected unreferenced run {job_b} unchecked"

        # The referenced output is pre-starred (exposed) — exactly one star active.
        assert self.count_active_output_stars() == 1, "Expected exactly the referenced output pre-starred"
        self.components.workflow_extract.output_star_active_for_job(job_id=job_a).wait_for_present()

        workflow_name = "Selenium Notebook Seeded"
        self.extract_workflow_name_and_submit(workflow_name)

        # Only run A's subgraph extracted: a single cat1 step with its two inputs.
        workflow = self.get_workflow_by_name(workflow_name)
        self.assert_cat1_workflow_structure(workflow)

    @selenium_test
    @managed_history
    def test_extract_button_visible_in_notebook_editor(self):
        """The Extract Workflow toolbar action is present when editing a notebook."""
        history_id = self.current_history_id()
        page = self.dataset_populator.new_history_page(history_id, content="# Notebook")

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.components.pages.history.extract_workflow_button.wait_for_visible()
        self.screenshot("notebook_extract_button_visible")

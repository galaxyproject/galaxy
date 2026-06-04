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
        # Capture the source notebook (its history_dataset_display directive names
        # the referenced output) alongside the Extract Workflow toolbar action —
        # the "before" frame that motivates the seeded form below.
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("notebook_extract_seeded_notebook")
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

    @skip_without_tool("random_lines1")
    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_notebook_seeds_referenced_mapped_subgraph(self):
        """Referencing a map-over output collection seeds the mapped (ICJ) card.

        A mapped tool card is keyed by ``data-icj-id`` and extracts via
        ``implicit_collection_jobs_ids`` rather than ``job_ids`` — a different UI
        object than the plain cat1 card the other seeded test drives. This proves
        the seeded pre-check reaches that card and the round-trip extracts the
        mapped subgraph, while an independent unreferenced cat1 run stays off.
        """
        history_id = self.current_history_id()
        output_hdca_id = self.run_random_lines_mapped(history_id)
        cat1_job_id, _ = self.run_cat1(history_id)
        page = self.dataset_populator.new_notebook_referencing(history_id, collection_ids=[output_hdca_id])

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.notebook_click_extract_workflow()
        self.screenshot("notebook_extract_seeded_mapped_form")

        # Both tool cards render (mapped random_lines1 + plain cat1); only the
        # referenced mapped subgraph is pre-checked.
        assert self.count_job_checkboxes() == 2, "Expected mapped and cat1 tool cards to render"
        assert self.count_checked_job_checkboxes() == 1, "Expected only the referenced mapped run pre-checked"

        mapped_card = self.components.workflow_extract.mapped_tool_card.wait_for_present()
        icj_id = mapped_card.get_attribute("data-icj-id")
        assert icj_id, "mapped-tool card missing data-icj-id"
        mapped_checkbox = self.components.workflow_extract.card_checkbox_by_icj_id(icj_id=icj_id).wait_for_present()
        assert mapped_checkbox.is_selected(), "Expected referenced mapped run pre-checked"

        cat1_checkbox = self.components.workflow_extract.card_checkbox_by_job_id(job_id=cat1_job_id).wait_for_present()
        assert not cat1_checkbox.is_selected(), "Expected unreferenced cat1 run unchecked"

        # The referenced output collection is pre-starred — exactly one star active.
        assert self.count_active_output_stars() == 1, "Expected exactly the referenced collection pre-starred"

        workflow_name = "Selenium Notebook Seeded Mapped"
        self.extract_workflow_name_and_submit(workflow_name)

        # Only the mapped subgraph extracted: a paired collection input + one
        # random_lines1 tool step; the cat1 run is excluded.
        workflow = self.get_workflow_by_name(workflow_name)
        assert len(workflow["steps"]) == 2, f"Expected 2 steps, got {len(workflow['steps'])}"
        self.assert_input_step_collection_type(workflow, "paired")
        tool_steps = self.assert_steps_of_type(workflow, "tool", expected_len=1)
        assert tool_steps[0]["tool_id"] == "random_lines1", tool_steps[0]

    @selenium_test
    @managed_history
    def test_extract_button_visible_in_notebook_editor(self):
        """The Extract Workflow toolbar action is present when editing a notebook."""
        history_id = self.current_history_id()
        page = self.dataset_populator.new_history_page(history_id, content="# Notebook")

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.components.pages.history.extract_workflow_button.wait_for_visible()

"""Selenium tests for extracting a workflow from a notebook (history-attached page)."""

from galaxy_test.base.populators import skip_without_tool
from galaxy_test.base.workflow_assertions import WorkflowStructureAssertions
from .framework import (
    ExtractsWorkflows,
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestNotebookWorkflowExtraction(SeleniumTestCase, ExtractsWorkflows, WorkflowStructureAssertions):
    ensure_registered = True

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_notebook_seeds_referenced_subgraph(self):
        """Referencing one of two independent runs pre-checks and pre-stars only that run."""
        history_id = self.current_history_id()
        job_a, output_a, job_b = self.setup_two_independent_cat1_runs(history_id)
        page = self.dataset_populator.new_notebook_referencing(history_id, [output_a])

        self.navigate_to_history_page_editor(history_id, page["id"])
        # Wait for the tool panel too, or its loading spinner leaks into the screenshot.
        self.components.pages.history.extract_workflow_button.wait_for_visible()
        self.components.tool_panel.toolbox.wait_for_visible()
        self.screenshot("notebook_extract_seeded_notebook")
        self.notebook_click_extract_workflow()

        # The summary loads async; wait for the settled seeded state before capturing.
        checkbox_a = self.components.workflow_extract.card_checkbox_by_job_id(job_id=job_a).wait_for_present()
        checkbox_b = self.components.workflow_extract.card_checkbox_by_job_id(job_id=job_b).wait_for_present()
        self.components.workflow_extract.output_star_active_for_job(job_id=job_a).wait_for_present()
        self.screenshot("notebook_extract_seeded_form")

        # Without from_page seeding the form would check both runs.
        assert self.count_job_checkboxes() == 2, "Expected both cat1 tool cards to render"
        assert self.count_checked_job_checkboxes() == 1, "Expected only the referenced run pre-checked"
        assert checkbox_a.is_selected(), f"Expected referenced run {job_a} pre-checked"
        assert not checkbox_b.is_selected(), f"Expected unreferenced run {job_b} unchecked"

        assert self.count_active_output_stars() == 1, "Expected exactly the referenced output pre-starred"
        star_a = self.components.workflow_extract.output_star_for_job(job_id=job_a).wait_for_present()
        assert star_a.get_attribute("aria-disabled") == "true", "Expected the report-used output's star locked"
        assert "notebook report uses this output" in (star_a.get_attribute("data-title") or "")

        workflow_name = "Selenium Notebook Seeded"
        self.extract_workflow_name_and_submit(workflow_name)

        workflow = self.get_workflow_by_name(workflow_name)
        self.assert_cat1_workflow_structure(workflow)

    @skip_without_tool("random_lines1")
    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_notebook_seeds_referenced_mapped_subgraph(self):
        """Referencing a map-over output collection pre-checks the mapped (ICJ) card only."""
        history_id = self.current_history_id()
        output_hdca_id = self.run_random_lines_mapped(history_id)
        cat1_job_id, _ = self.run_cat1(history_id)
        page = self.dataset_populator.new_notebook_referencing(history_id, collection_ids=[output_hdca_id])

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.notebook_click_extract_workflow()

        # The summary loads async; wait for the settled seeded state before capturing.
        mapped_card = self.components.workflow_extract.mapped_tool_card.wait_for_present()
        self.components.workflow_extract.all_active_output_stars.wait_for_present()
        self.screenshot("notebook_extract_seeded_mapped_form")

        assert self.count_job_checkboxes() == 2, "Expected mapped and cat1 tool cards to render"
        assert self.count_checked_job_checkboxes() == 1, "Expected only the referenced mapped run pre-checked"

        icj_id = mapped_card.get_attribute("data-icj-id")
        assert icj_id, "mapped-tool card missing data-icj-id"
        mapped_checkbox = self.components.workflow_extract.card_checkbox_by_icj_id(icj_id=icj_id).wait_for_present()
        assert mapped_checkbox.is_selected(), "Expected referenced mapped run pre-checked"

        cat1_checkbox = self.components.workflow_extract.card_checkbox_by_job_id(job_id=cat1_job_id).wait_for_present()
        assert not cat1_checkbox.is_selected(), "Expected unreferenced cat1 run unchecked"

        assert self.count_active_output_stars() == 1, "Expected exactly the referenced collection pre-starred"

        workflow_name = "Selenium Notebook Seeded Mapped"
        self.extract_workflow_name_and_submit(workflow_name)

        workflow = self.get_workflow_by_name(workflow_name)
        assert len(workflow["steps"]) == 2, f"Expected 2 steps, got {len(workflow['steps'])}"
        self.assert_input_step_collection_type(workflow, "paired")
        tool_steps = self.assert_steps_of_type(workflow, "tool", expected_len=1)
        assert tool_steps[0]["tool_id"] == "random_lines1", tool_steps[0]

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_notebook_report_renders_the_invocations_own_output(self):
        """Extract from a notebook, run the workflow on fresh data; the report shows the new output, not the notebook's."""
        history_id = self.current_history_id()
        run = self.dataset_populator.run_cat1(history_id, ("notebook-alpha", "notebook-beta"))
        page = self.dataset_populator.new_notebook_referencing(history_id, output_ids=[run.output_id])

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.notebook_click_extract_workflow()
        self.components.workflow_extract.output_star_active_for_job(job_id=run.job_id).wait_for_present()
        workflow_name = "Selenium Notebook Report Round Trip"
        self.extract_workflow_name_and_submit(workflow_name)
        workflow_id = self.find_workflow_by_name(workflow_name)

        invocation_history_id = self.dataset_populator.new_history()
        fresh = [
            self.dataset_populator.new_dataset(invocation_history_id, content=content)
            for content in ("fresh-alpha\n", "fresh-beta\n")
        ]
        self.dataset_populator.wait_for_history(invocation_history_id, assert_ok=True)
        invocation_id = self.workflow_populator.invoke_workflow_and_assert_ok(
            workflow_id,
            history_id=invocation_history_id,
            inputs={str(index): {"src": "hda", "id": dataset["id"]} for index, dataset in enumerate(fresh)},
            inputs_by="step_index",
        )
        self.workflow_populator.wait_for_invocation_and_jobs(
            history_id=invocation_history_id, workflow_id=workflow_id, invocation_id=invocation_id
        )

        self.get(f"workflows/invocations/report?id={invocation_id}")
        self.wait_for_selector_visible(".markdown-component")
        self.wait_for_xpath_visible('//*[contains(@class, "markdown-component")]//*[contains(text(), "fresh-alpha")]')
        self.screenshot("notebook_extract_report_round_trip")
        report_text = self.find_element_by_selector(".markdown-component").text
        assert "Analysis" in report_text, report_text
        assert "notebook-alpha" not in report_text, report_text

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_notebook_report_warnings_show_as_a_toast(self):
        """Report lines the extraction drops are reported to the user, not lost silently."""
        history_id = self.current_history_id()
        job_id, output_id = self.run_cat1(history_id)
        page = self.dataset_populator.new_history_page(
            history_id,
            content=(
                "# Analysis\n\n"
                f"Merged ${{galaxy history_dataset_name(history_dataset_id={output_id})}}.\n\n"
                f"```galaxy\nhistory_dataset_display(history_dataset_id={output_id})\n```\n"
            ),
        )

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.notebook_click_extract_workflow()
        self.components.workflow_extract.output_star_active_for_job(job_id=job_id).wait_for_present()
        self.extract_workflow_name_and_submit("Selenium Notebook Report Warnings")

        toast = self.components.workflow_extract.report_notes_toast.wait_for_visible()
        self.screenshot("notebook_extract_report_warnings_toast")
        assert "Dropped an inline [history_dataset_name] reference" in toast.text, toast.text

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_notebook_seeds_copied_in_output_as_input(self):
        """A tool output copied in from another history becomes a pre-checked input wired to its consumer."""
        source_history_id = self.dataset_populator.new_history()
        _, source_output_id = self.run_cat1(source_history_id)
        history_id = self.current_history_id()
        copied = self.dataset_populator.copy_dataset(history_id, source_output_id)
        run = self.dataset_populator.run_tool("cat1", {"input1": {"src": "hda", "id": copied["id"]}}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        page = self.dataset_populator.new_notebook_referencing(history_id, output_ids=[run["outputs"][0]["id"]])

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.notebook_click_extract_workflow()
        self.components.workflow_extract.card_checkbox_by_job_id(job_id=run["jobs"][0]["id"]).wait_for_present()
        self.components.workflow_extract.input_card_checkbox_checked.wait_for_present()
        self.screenshot("notebook_extract_copied_input_form")

        assert len(self.components.workflow_extract.input_card_checkbox_checked.all()) == 1
        assert self.count_checked_job_checkboxes() == 1, "Expected only the consuming cat1 run pre-checked"

        workflow_name = "Selenium Notebook Copied Input"
        self.extract_workflow_name_and_submit(workflow_name)
        workflow = self.get_workflow_by_name(workflow_name)
        input_steps = self.assert_steps_of_type(workflow, "data_input", expected_len=1)
        tool_steps = self.assert_steps_of_type(workflow, "tool", expected_len=1)
        connection = tool_steps[0]["input_connections"]["input1"]
        connection = connection[0] if isinstance(connection, list) else connection
        assert connection["id"] == input_steps[0]["id"], tool_steps[0]

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_notebook_referencing_nothing_explains_empty_seed(self):
        """A notebook referencing nothing shows the no-seed message with every card unchecked."""
        history_id = self.current_history_id()
        self.run_cat1(history_id)
        page = self.dataset_populator.new_history_page(history_id, content="# Notebook\n\nNo directives here.\n")

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.notebook_click_extract_workflow()

        # The summary loads async; wait for the settled empty-seed state before capturing.
        self.components.workflow_extract.no_seed_message.wait_for_visible()
        self.components.workflow_extract.tool_card_checkbox.wait_for_present()
        self.screenshot("notebook_extract_no_seed_form")

        assert self.count_job_checkboxes() >= 1, "Expected the cat1 tool card to render"
        assert self.count_checked_job_checkboxes() == 0, "Expected nothing pre-checked when the notebook seeds nothing"

    @selenium_test
    @managed_history
    def test_extract_button_visible_in_notebook_editor(self):
        history_id = self.current_history_id()
        page = self.dataset_populator.new_history_page(history_id, content="# Notebook")

        self.navigate_to_history_page_editor(history_id, page["id"])
        self.components.pages.history.extract_workflow_button.wait_for_visible()

"""Selenium tests for the Jobs activity panel.

The Jobs panel (client/src/components/Panels/JobPanel.vue) lists the current
user's jobs, kept reactively in sync with a shared `jobStore` cache, and lets
the user filter by tool id/name and job state. These tests drive it end to end
against a live server: run real tools, open the panel, and assert the job
cards/filtering behave as expected.
"""

from galaxy_test.base.populators import skip_without_tool
from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class TestJobPanel(SeleniumTestCase):
    ensure_registered = True

    def _run_cat1(self, history_id: str) -> str:
        """Run cat1 over two fresh uploads. Returns the job id."""
        hda1 = self.dataset_populator.new_dataset(history_id, content="foo\nbar", wait=True)
        hda2 = self.dataset_populator.new_dataset(history_id, content="baz", wait=True)
        inputs = {"input1": {"src": "hda", "id": hda1["id"]}, "queries_0|input2": {"src": "hda", "id": hda2["id"]}}
        run = self.dataset_populator.run_tool("cat1", inputs, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return run["jobs"][0]["id"]

    def _run_random_lines1(self, history_id: str) -> str:
        """Run random_lines1 over a single fresh upload. Returns the job id."""
        hda = self.dataset_populator.new_dataset(history_id, content="1\n2\n3\n4\n5", wait=True)
        inputs = {"input": {"src": "hda", "id": hda["id"]}, "num_lines": 2}
        run = self.dataset_populator.run_tool("random_lines1", inputs, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return run["jobs"][0]["id"]

    def _open_job_panel(self):
        job_panel = self.components.job_panel
        self._ensure_panel_open(job_panel.panel, job_panel.activity.wait_for_and_click)

    @retry_assertion_during_transitions
    def _assert_job_card_visible(self, job_id: str, tool_id: str):
        self.components.job_panel.job_card(job_id=job_id).wait_for_present()
        title = self.components.job_panel.job_card_title(job_id=job_id).wait_for_text()
        assert title == tool_id, f"Expected job card title to be [{tool_id}], got [{title}]"

    @retry_assertion_during_transitions
    def _assert_job_card_state(self, job_id: str, state: str):
        state_text = self.components.job_panel.job_card_state(job_id=job_id).wait_for_text()
        assert state in state_text, f"Expected job card state to contain [{state}], got [{state_text}]"

    @retry_assertion_during_transitions
    def _assert_job_card_absent(self, job_id: str):
        self.components.job_panel.job_card(job_id=job_id).assert_absent()

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_job_appears_in_panel_after_running_a_tool(self):
        history_id = self.current_history_id()
        job_id = self._run_cat1(history_id)

        self._open_job_panel()

        self._assert_job_card_visible(job_id, "cat1")
        self._assert_job_card_state(job_id, "ok")

    @skip_without_tool("cat1")
    @skip_without_tool("random_lines1")
    @selenium_test
    @managed_history
    def test_filter_jobs_by_tool_id(self):
        history_id = self.current_history_id()
        cat1_job_id = self._run_cat1(history_id)
        random_lines_job_id = self._run_random_lines1(history_id)

        self._open_job_panel()

        self._assert_job_card_visible(cat1_job_id, "cat1")
        self._assert_job_card_visible(random_lines_job_id, "random_lines1")

        self._inline_search_for(self.navigation.job_panel.search_input, "tool_id:cat1", escape_to_clear=True)

        self._assert_job_card_visible(cat1_job_id, "cat1")
        self._assert_job_card_absent(random_lines_job_id)

        # Clearing the filter brings the other job back into view.
        self._inline_search_for(self.navigation.job_panel.search_input, None, escape_to_clear=True)

        self._assert_job_card_visible(cat1_job_id, "cat1")
        self._assert_job_card_visible(random_lines_job_id, "random_lines1")

    @skip_without_tool("cat1")
    @skip_without_tool("random_lines1")
    @selenium_test
    @managed_history
    def test_search_jobs_by_tool_name(self):
        history_id = self.current_history_id()
        cat1_job_id = self._run_cat1(history_id)
        random_lines_job_id = self._run_random_lines1(history_id)

        self._open_job_panel()
        self.components.job_panel.name_mode_toggle.wait_for_and_click()

        self._assert_job_card_visible(cat1_job_id, "Concatenate multiple datasets or collections")

        self._inline_search_for(self.navigation.job_panel.search_input, "'Select random lines'", escape_to_clear=True)

        self._assert_job_card_visible(random_lines_job_id, "Select random lines")
        self._assert_job_card_absent(cat1_job_id)

    @skip_without_tool("cat1")
    @selenium_test
    @managed_history
    def test_filter_by_invalid_filter_key_shows_an_error_instead_of_the_unfiltered_list(self):
        history_id = self.current_history_id()
        job_id = self._run_cat1(history_id)

        self._open_job_panel()
        self._assert_job_card_visible(job_id, "cat1")

        self._inline_search_for(self.navigation.job_panel.search_input, "xx:ss", escape_to_clear=True)

        # The invalid filter must not silently fall back to showing every job.
        self._assert_job_card_absent(job_id)
        alert_text = self.components.job_panel.error_alert.wait_for_text()
        assert "Invalid filter(s) in query: xx" in alert_text, alert_text

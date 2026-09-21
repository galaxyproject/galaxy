"""E2E tests for the GalaxyAI learning mode ("tutor") toggle.

Uses the static agent backend for deterministic assertions -- no LLM calls.
Skipped when agents are not configured (skip_without_agents decorator).
"""

from contextlib import contextmanager

from galaxy_test.base.populators import skip_without_agents
from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)

LEARNING_ASSISTANT_LABEL = "Learning Assistant"
ROUTER_LABEL = "Router"
TUTOR_RESPONSE = "Before I explain, what do you already know about this step?"


class TestLearningMode(SeleniumTestCase):
    ensure_registered = True

    @skip_without_agents
    @selenium_test
    def test_toggle_persists_across_reloads(self):
        """Turning learning mode on stores it server-side and survives a reload."""
        self._reset_learning_state()
        galaxyai = self.components.galaxyai

        self.navigate_to_galaxyai()
        galaxyai._.wait_for_visible()
        with self._learning_mode_on():
            galaxyai.learning_mode_scaffolding.wait_for_visible()
            assert self.api_get("chat/tutor/state")["tutor_mode_enabled"] is True

            # Full reload -- the toggle state comes back from the server, not the browser.
            self.navigate_to_galaxyai()
            galaxyai._.wait_for_visible()
            self.galaxyai_wait_for_learning_mode(True)

            self.galaxyai_set_learning_mode(False)
            galaxyai.learning_mode_scaffolding.wait_for_absent_or_hidden()
            assert self.api_get("chat/tutor/state")["tutor_mode_enabled"] is False

    @skip_without_agents
    @selenium_test
    def test_toggle_switches_answering_agent(self):
        """Learning mode routes answers to the teaching assistant, off routes back to the router."""
        self._reset_learning_state()
        galaxyai = self.components.galaxyai

        self.navigate_to_galaxyai()
        self.galaxyai_ensure_new_chat()
        with self._learning_mode_on():
            self.galaxyai_send_message("Hello!")

            @retry_assertion_during_transitions
            def assert_tutor_answered():
                assert galaxyai.agent_label.all()[-1].text == LEARNING_ASSISTANT_LABEL
                assert TUTOR_RESPONSE in galaxyai.response_content.all()[-1].text

            assert_tutor_answered()

            self.galaxyai_set_learning_mode(False)
            self.galaxyai_send_message("Hello!")

            @retry_assertion_during_transitions
            def assert_router_answered():
                assert len(galaxyai.agent_label.all()) == 2
                assert galaxyai.agent_label.all()[-1].text == ROUTER_LABEL

            assert_router_answered()

    @skip_without_agents
    @selenium_test
    def test_docked_panel_shows_job_context(self):
        """A job page hands the docked panel its job as context without hijacking the tutor."""
        self._reset_learning_state()
        galaxyai = self.components.galaxyai

        history_id = self.current_history_id()
        dataset = self.dataset_populator.new_dataset(history_id, content="1\t2\t3", wait=True)
        job_id = self.api_get(f"datasets/{dataset['id']}")["creating_job"]

        self.galaxyai_dock_to_side_panel()
        self.driver.get(self.build_url(f"jobs/{job_id}/view"))
        galaxyai.docked_panel.wait_for_visible()

        galaxyai.context_badge.wait_for_visible()
        galaxyai.context_badge.assert_data_value("context-type", "job")
        galaxyai.context_badge.assert_data_value("context-id", job_id)

        with self._learning_mode_on():
            self.galaxyai_send_message("Hello!")

            @retry_assertion_during_transitions
            def assert_tutor_answered():
                assert galaxyai.agent_label.all()[-1].text == LEARNING_ASSISTANT_LABEL

            assert_tutor_answered()

            galaxyai.context_dismiss.wait_for_and_click()
            galaxyai.context_badge.wait_for_absent_or_hidden()

    def _reset_learning_state(self):
        self.api_put("chat/tutor/state", {"tutor_mode_enabled": False})
        self.api_delete("chat/history")

    @contextmanager
    def _learning_mode_on(self):
        self.galaxyai_set_learning_mode(True)
        try:
            yield
        finally:
            # A configured selenium account is shared by every module, so the tutor
            # must come back off even when an assertion fails partway through.
            self.api_put("chat/tutor/state", {"tutor_mode_enabled": False})

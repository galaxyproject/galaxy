"""E2E tests for the GalaxyWizard inline error analysis widget.

Uses the static agent backend for deterministic assertions — no LLM calls.
Skipped when agents are not configured (skip_without_agents decorator).
"""

from galaxy_test.base.populators import skip_without_agents
from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class TestGalaxyWizard(SeleniumTestCase):
    ensure_registered = True

    def create_failed_dataset(self):
        """Run detect_errors tool with stderr output to produce a failed dataset."""
        history_id = self.current_history_id()
        inputs = {
            "stdoutmsg": "",
            "stderrmsg": "error: tool configuration failure detected",
            "exit_code": "6",
        }
        response = self.dataset_populator.run_tool("detect_errors", inputs, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=False)
        failed_hid = response["outputs"][0]["hid"]
        return history_id, failed_hid

    @skip_without_agents
    @selenium_test
    @managed_history
    def test_wizard_error_analysis_flow(self):
        """Create failed dataset, analyze error, verify response and feedback."""
        # Setup: create a failed dataset via API
        history_id, failed_hid = self.create_failed_dataset()
        self.history_panel_wait_for_hid_state(failed_hid, "error")
        self.screenshot("galaxy_wizard_error_dataset_in_history")

        # Navigate to error view
        self.navigate_to_dataset_error(failed_hid)
        wizard = self.components.galaxy_wizard

        # Wizard section visible (agents configured)
        wizard.analyze_button.wait_for_visible()
        self.screenshot("galaxy_wizard_before_analyze")

        # Click analyze, wait for response
        self.galaxy_wizard_analyze()
        self.screenshot("galaxy_wizard_response_received")

        # Verify response content from static backend
        @retry_assertion_during_transitions
        def assert_response():
            assert "tool configuration issue" in wizard.response.wait_for_text()

        assert_response()

        # Feedback
        wizard.feedback_up.wait_for_and_click()

        @retry_assertion_during_transitions
        def assert_feedback():
            assert "Thank you" in wizard.feedback_ack.wait_for_text()

        assert_feedback()
        self.screenshot("galaxy_wizard_feedback_submitted")

"""E2E tests for the ChatGXY conversational AI interface.

Uses the static agent backend for deterministic assertions — no LLM calls.
Skipped when agents are not configured (skip_without_agents decorator).
"""

from galaxy_test.base.populators import skip_without_agents
from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)


class TestChatGXY(SeleniumTestCase):
    ensure_registered = True

    @skip_without_agents
    @selenium_test
    def test_chat_greeting_flow(self):
        """Activity visible, send greeting, get response, give feedback, check metadata."""
        self.home()
        chatgxy = self.components.chatgxy

        # Activity bar icon visible
        chatgxy.activity.wait_for_visible()

        # Navigate, start fresh
        self.navigate_to_chatgxy()
        self.chatgxy_ensure_new_chat()

        # Send greeting
        self.chatgxy_send_message("Hello!")

        # Verify query cell and response
        assert chatgxy.query_cell.wait_for_text() == "Hello!"

        @retry_assertion_during_transitions
        def assert_response():
            assert "Hello" in chatgxy.response_content.wait_for_text()

        assert_response()

        # Agent indicator and metadata tags present
        chatgxy.agent_indicator.wait_for_visible()
        assert len(chatgxy.meta_tag.all()) >= 1

        # Feedback
        chatgxy.feedback_up.wait_for_and_click()
        assert "Thanks" in chatgxy.feedback_ack.wait_for_text()

    @skip_without_agents
    @selenium_test
    def test_multi_turn_and_new_chat(self):
        """Two queries build up conversation, 'New' resets it."""
        self.navigate_to_chatgxy()
        self.chatgxy_ensure_new_chat()
        chatgxy = self.components.chatgxy

        self.chatgxy_send_message("Hello!")
        self.chatgxy_send_message("How do I analyze RNA-seq data?")

        @retry_assertion_during_transitions
        def assert_two_exchanges():
            assert len(chatgxy.query_cell.all()) == 2
            responses = chatgxy.response_content.all()
            assert len(responses) >= 2
            # Second response should be domain-specific
            assert "HISAT2" in responses[-1].text or "RNA-seq" in responses[-1].text

        assert_two_exchanges()

        # New chat resets
        chatgxy.new_chat_button.wait_for_and_click()
        self._chatgxy_assert_chat_empty()

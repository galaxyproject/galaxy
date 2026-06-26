"""Unit tests for the tutor analytics aggregation."""

import json
from types import SimpleNamespace

from galaxy.managers.tutor_analytics import (
    TUTOR_AGENT_TYPE,
    TutorAnalyticsManager,
)


def _msg(exchange_id, agent_type, feedback=None):
    return SimpleNamespace(
        chat_exchange_id=exchange_id,
        feedback=feedback,
        message=json.dumps({"query": "q", "response": "r", "agent_type": agent_type}),
    )


class TestTutorAnalytics:
    def setup_method(self):
        self.manager = TutorAnalyticsManager()

    def test_agent_type_parsing(self):
        assert self.manager._agent_type(json.dumps({"agent_type": "teaching_assistant"})) == "teaching_assistant"
        assert self.manager._agent_type("not json{{") == "unknown"
        assert self.manager._agent_type(json.dumps(["a", "b"])) == "unknown"
        assert self.manager._agent_type(json.dumps({"query": "q"})) == "unknown"

    def test_empty_inputs(self):
        result = self.manager._aggregate([], [])
        assert result["total_messages"] == 0
        assert result["tutor_messages"] == 0
        assert result["tutor_message_share"] == 0.0
        assert result["avg_conversation_length"]["tutor"] == 0.0
        assert result["avg_conversation_length"]["task"] == 0.0

    def test_counts_tutor_vs_task(self):
        messages = [
            _msg(1, TUTOR_AGENT_TYPE, feedback=1),
            _msg(1, TUTOR_AGENT_TYPE, feedback=0),
            _msg(2, "router"),
            _msg(3, "error_analysis"),
        ]
        result = self.manager._aggregate(messages, [])
        assert result["total_messages"] == 4
        assert result["tutor_messages"] == 2
        assert result["tutor_message_share"] == 0.5
        assert result["tutor_feedback"] == {"positive": 1, "negative": 1, "none": 0}
        # exchange 1 is a tutor exchange (2 messages); 2 and 3 are task exchanges (1 each)
        assert result["avg_conversation_length"]["tutor"] == 2.0
        assert result["avg_conversation_length"]["task"] == 1.0

    def test_learning_state_distribution(self):
        states = [
            {"tutor_mode_enabled": True, "scaffolding_level": 3, "expertise_level": "beginner"},
            {"tutor_mode_enabled": True, "scaffolding_level": 2, "expertise_level": "intermediate"},
            {"tutor_mode_enabled": False, "scaffolding_level": 3, "expertise_level": "beginner"},
        ]
        result = self.manager._aggregate([], states)
        assert result["learning_state_users"] == 2
        assert result["scaffolding_distribution"] == {3: 2, 2: 1}
        assert result["expertise_distribution"] == {"beginner": 2, "intermediate": 1}

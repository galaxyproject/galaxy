"""Analytics for the cognitive tutor, computed from existing tables.

Aggregates the GalaxyAI conversation log (``ChatExchange`` /
``ChatExchangeMessage``) together with the per-user ``learning_state``
preference. No new tables are introduced -- this is a read-only view over data
the tutor already records.
"""

import json
import logging
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.learning_state import (
    DEFAULT_LEARNING_STATE,
    LEARNING_STATE_KEY,
)
from galaxy.model import (
    ChatExchangeMessage,
    UserPreference,
)

log = logging.getLogger(__name__)

TUTOR_AGENT_TYPE = "teaching_assistant"


class TutorAnalyticsManager:
    """Aggregate tutor usage metrics from existing chat and preference tables."""

    def get_analytics(self, trans: ProvidesUserContext) -> dict[str, Any]:
        messages = trans.sa_session.execute(select(ChatExchangeMessage)).scalars().all()
        states = self._learning_states(trans)
        return self._aggregate(messages, states)

    def _aggregate(self, messages: Iterable[Any], states: Iterable[dict[str, Any]]) -> dict[str, Any]:
        """Pure aggregation over message rows and learning-state dicts.

        Kept free of the database so it can be unit-tested directly. Each message
        is expected to expose ``message`` (JSON string), ``feedback`` (0/1/None),
        and ``chat_exchange_id``.
        """
        total_messages = 0
        tutor_messages = 0
        tutor_feedback = {"positive": 0, "negative": 0, "none": 0}
        exchange_msg_counts: dict[int, int] = {}
        tutor_exchange_ids: set[int] = set()

        for msg in messages:
            total_messages += 1
            exchange_msg_counts[msg.chat_exchange_id] = exchange_msg_counts.get(msg.chat_exchange_id, 0) + 1
            if self._agent_type(msg.message) == TUTOR_AGENT_TYPE:
                tutor_messages += 1
                tutor_exchange_ids.add(msg.chat_exchange_id)
                if msg.feedback == 1:
                    tutor_feedback["positive"] += 1
                elif msg.feedback == 0:
                    tutor_feedback["negative"] += 1
                else:
                    tutor_feedback["none"] += 1

        tutor_lengths = [c for eid, c in exchange_msg_counts.items() if eid in tutor_exchange_ids]
        task_lengths = [c for eid, c in exchange_msg_counts.items() if eid not in tutor_exchange_ids]

        tutor_enabled_users = 0
        total_interactions = 0
        total_demonstrations = 0
        scaffolding_distribution: dict[int, int] = {}
        expertise_distribution: dict[str, int] = {}
        for state in states:
            if state.get("tutor_mode_enabled"):
                tutor_enabled_users += 1
            total_interactions += state.get("interaction_count", 0)
            total_demonstrations += state.get("demonstrations_count", 0)
            level = state.get("scaffolding_level", DEFAULT_LEARNING_STATE["scaffolding_level"])
            scaffolding_distribution[level] = scaffolding_distribution.get(level, 0) + 1
            expertise = state.get("expertise_level", DEFAULT_LEARNING_STATE["expertise_level"])
            expertise_distribution[expertise] = expertise_distribution.get(expertise, 0) + 1

        return {
            "total_messages": total_messages,
            "tutor_messages": tutor_messages,
            "tutor_message_share": (tutor_messages / total_messages) if total_messages else 0.0,
            "tutor_feedback": tutor_feedback,
            "avg_conversation_length": {
                "tutor": (sum(tutor_lengths) / len(tutor_lengths)) if tutor_lengths else 0.0,
                "task": (sum(task_lengths) / len(task_lengths)) if task_lengths else 0.0,
            },
            "learning_state_users": tutor_enabled_users,
            "scaffolding_distribution": scaffolding_distribution,
            "expertise_distribution": expertise_distribution,
            # Empower-vs-dependence signal: how often learners are shown vs. guided.
            "total_interactions": total_interactions,
            "total_demonstrations": total_demonstrations,
            "demonstration_reliance": (total_demonstrations / total_interactions) if total_interactions else 0.0,
        }

    def _agent_type(self, message: str) -> str:
        try:
            data = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return "unknown"
        if isinstance(data, dict):
            return data.get("agent_type", "unknown")
        return "unknown"

    def _learning_states(self, trans: ProvidesUserContext) -> list[dict[str, Any]]:
        stmt = select(UserPreference).where(UserPreference.name == LEARNING_STATE_KEY)
        prefs = trans.sa_session.execute(stmt).scalars().all()
        states: list[dict[str, Any]] = []
        for pref in prefs:
            try:
                states.append(json.loads(pref.value))
            except (json.JSONDecodeError, TypeError):
                continue
        return states

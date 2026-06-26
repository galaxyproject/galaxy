"""
Learning state management for the AI cognitive tutor.

Stores per-user learning progress in UserPreference as JSON,
avoiding the need for database migrations. The learning state
tracks expertise level, completed tutorials, current pathway
progress, and scaffolding preferences.
"""

import json
import logging
from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
    Optional,
)

from galaxy.managers.context import ProvidesUserContext

log = logging.getLogger(__name__)

LEARNING_STATE_KEY = "learning_state"

DEFAULT_LEARNING_STATE: dict[str, Any] = {
    "expertise_level": "beginner",
    "scaffolding_level": 3,
    "completed_tutorials": [],
    "current_pathway": None,
    "pathway_progress": {},
    "topics_explored": [],
    "interaction_count": 0,
    "tutor_mode_enabled": False,
    "last_interaction": None,
}


class LearningStateManager:
    """Manages per-user learning state via UserPreference storage."""

    def get_learning_state(self, trans: ProvidesUserContext) -> dict[str, Any]:
        """Get the current learning state for the user."""
        user = trans.user
        if user is None:
            return dict(DEFAULT_LEARNING_STATE)

        pref = self._get_preference(trans, LEARNING_STATE_KEY)
        if pref is None:
            return dict(DEFAULT_LEARNING_STATE)

        try:
            state = json.loads(pref)
            # Merge with defaults to handle schema evolution
            merged = dict(DEFAULT_LEARNING_STATE)
            merged.update(state)
            return merged
        except (json.JSONDecodeError, TypeError):
            log.warning(f"Corrupted learning state for user {user.id}, returning defaults")
            return dict(DEFAULT_LEARNING_STATE)

    def update_learning_state(self, trans: ProvidesUserContext, updates: dict[str, Any]) -> dict[str, Any]:
        """Partially update the learning state. Returns the full updated state."""
        state = self.get_learning_state(trans)
        state.update(updates)
        state["last_interaction"] = datetime.now(timezone.utc).isoformat()
        self._set_preference(trans, LEARNING_STATE_KEY, json.dumps(state))
        return state

    def record_interaction(self, trans: ProvidesUserContext) -> dict[str, Any]:
        """Increment interaction count and update timestamp."""
        state = self.get_learning_state(trans)
        state["interaction_count"] = state.get("interaction_count", 0) + 1
        state["last_interaction"] = datetime.now(timezone.utc).isoformat()
        self._set_preference(trans, LEARNING_STATE_KEY, json.dumps(state))
        return state

    def record_tutorial_completion(
        self, trans: ProvidesUserContext, tutorial_id: str, topic: Optional[str] = None
    ) -> dict[str, Any]:
        """Record that a user completed a tutorial."""
        state = self.get_learning_state(trans)
        completed = state.get("completed_tutorials", [])
        if tutorial_id not in completed:
            completed.append(tutorial_id)
            state["completed_tutorials"] = completed

        if topic:
            topics = state.get("topics_explored", [])
            if topic not in topics:
                topics.append(topic)
                state["topics_explored"] = topics

            # Advance pathway progress if on this topic
            progress = state.get("pathway_progress", {})
            current_step = progress.get(topic, 0)
            progress[topic] = current_step + 1
            state["pathway_progress"] = progress

        state["last_interaction"] = datetime.now(timezone.utc).isoformat()
        self._maybe_adjust_expertise(state)
        self._set_preference(trans, LEARNING_STATE_KEY, json.dumps(state))
        return state

    def adjust_scaffolding(self, trans: ProvidesUserContext, direction: str) -> dict[str, Any]:
        """Adjust scaffolding level up (less support) or down (more support)."""
        state = self.get_learning_state(trans)
        current = state.get("scaffolding_level", 3)
        if direction == "up" and current < 5:
            state["scaffolding_level"] = current + 1
        elif direction == "down" and current > 1:
            state["scaffolding_level"] = current - 1
        self._set_preference(trans, LEARNING_STATE_KEY, json.dumps(state))
        return state

    def get_expertise_level(self, trans: ProvidesUserContext) -> str:
        """Get the inferred expertise level."""
        state = self.get_learning_state(trans)
        return state.get("expertise_level", "beginner")

    def enable_tutor_mode(self, trans: ProvidesUserContext) -> dict[str, Any]:
        """Enable tutor mode for the user."""
        return self.update_learning_state(trans, {"tutor_mode_enabled": True})

    def disable_tutor_mode(self, trans: ProvidesUserContext) -> dict[str, Any]:
        """Disable tutor mode for the user."""
        return self.update_learning_state(trans, {"tutor_mode_enabled": False})

    def set_current_pathway(self, trans: ProvidesUserContext, pathway: str) -> dict[str, Any]:
        """Set the user's current learning pathway."""
        return self.update_learning_state(trans, {"current_pathway": pathway})

    def _maybe_adjust_expertise(self, state: dict[str, Any]) -> None:
        """Infer expertise level from completed tutorials and interactions."""
        completed_count = len(state.get("completed_tutorials", []))
        interaction_count = state.get("interaction_count", 0)

        if completed_count >= 10 or interaction_count >= 100:
            state["expertise_level"] = "advanced"
        elif completed_count >= 3 or interaction_count >= 30:
            state["expertise_level"] = "intermediate"
        else:
            state["expertise_level"] = "beginner"

    def _get_preference(self, trans: ProvidesUserContext, key: str) -> Optional[str]:
        """Get a user preference value."""
        user = trans.user
        if user is None:
            return None
        for pref in user.preferences:
            if pref.name == key:
                return pref.value
        return None

    def _set_preference(self, trans: ProvidesUserContext, key: str, value: str) -> None:
        """Set a user preference value."""
        user = trans.user
        if user is None:
            return
        for pref in user.preferences:
            if pref.name == key:
                pref.value = value
                trans.sa_session.add(pref)
                trans.sa_session.flush()
                return
        # Create new preference
        from galaxy.model import UserPreference

        new_pref = UserPreference(name=key, value=value)
        new_pref.user_id = user.id
        trans.sa_session.add(new_pref)
        trans.sa_session.flush()

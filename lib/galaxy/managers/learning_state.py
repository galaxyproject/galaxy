"""
Learning state management for the AI cognitive tutor.

Stores per-user tutoring preferences and usage in UserPreference as JSON,
avoiding the need for database migrations. The learning state
tracks scaffolding preferences and interaction/demonstration counts.
"""

import json
import logging
from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
)

from galaxy.managers.context import ProvidesUserContext

log = logging.getLogger(__name__)

LEARNING_STATE_KEY = "learning_state"

DEFAULT_LEARNING_STATE: dict[str, Any] = {
    "scaffolding_level": 3,
    "interaction_count": 0,
    "demonstrations_count": 0,
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
            if not isinstance(state, dict):
                raise TypeError("Learning state must be an object")
            # Ignore retired fields, including expertise inferred from message counts.
            merged = dict(DEFAULT_LEARNING_STATE)
            merged.update({key: value for key, value in state.items() if key in merged})
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

    def record_demonstration(self, trans: ProvidesUserContext) -> dict[str, Any]:
        """Count a demonstration that submitted at least one job."""
        state = self.get_learning_state(trans)
        state["demonstrations_count"] = state.get("demonstrations_count", 0) + 1
        self._set_preference(trans, LEARNING_STATE_KEY, json.dumps(state))
        return state

    def enable_tutor_mode(self, trans: ProvidesUserContext) -> dict[str, Any]:
        """Enable tutor mode for the user."""
        return self.update_learning_state(trans, {"tutor_mode_enabled": True})

    def disable_tutor_mode(self, trans: ProvidesUserContext) -> dict[str, Any]:
        """Disable tutor mode for the user."""
        return self.update_learning_state(trans, {"tutor_mode_enabled": False})

    def _get_preference(self, trans: ProvidesUserContext, key: str) -> str | None:
        """Get a user preference value.

        ``user.preferences`` is an association proxy that behaves like a dict
        mapping preference name -> value.
        """
        user = trans.user
        if user is None:
            return None
        return user.preferences[key] if key in user.preferences else None

    def _set_preference(self, trans: ProvidesUserContext, key: str, value: str) -> None:
        """Set a user preference value and persist it."""
        user = trans.user
        if user is None:
            return
        user.preferences[key] = value
        trans.sa_session.commit()

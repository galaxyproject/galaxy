"""API tests for the cognitive tutor's learning-state endpoints.

These endpoints are plain per-user preference CRUD (no LLM required), so they run
against any Galaxy with a logged-in user.

## Running (auto-started server):
    ./run_tests.sh -api lib/galaxy_test/api/test_chat_tutor.py
"""

from ._framework import ApiTestCase

EXPECTED_STATE_KEYS = {
    "expertise_level",
    "scaffolding_level",
    "completed_tutorials",
    "current_pathway",
    "pathway_progress",
    "topics_explored",
    "interaction_count",
    "tutor_mode_enabled",
    "last_interaction",
}


class TestChatTutorApi(ApiTestCase):
    def _get_state(self) -> dict:
        response = self._get("chat/tutor/state")
        self._assert_status_code_is_ok(response)
        return response.json()

    def _set_mode(self, enabled: bool) -> dict:
        response = self._post("chat/tutor/mode", data={"enabled": enabled}, json=True)
        self._assert_status_code_is_ok(response)
        return response.json()

    def test_get_tutor_state_returns_full_shape(self):
        """GET /api/chat/tutor/state returns the learning-state dict with sane defaults."""
        state = self._get_state()
        assert EXPECTED_STATE_KEYS.issubset(state.keys())
        assert isinstance(state["scaffolding_level"], int)
        assert 1 <= state["scaffolding_level"] <= 5
        assert isinstance(state["expertise_level"], str)
        assert isinstance(state["tutor_mode_enabled"], bool)

    def test_toggle_tutor_mode_on_and_off(self):
        """POST /api/chat/tutor/mode flips tutor mode and persists it."""
        on = self._set_mode(True)
        assert on["enabled"] is True
        assert on["state"]["tutor_mode_enabled"] is True
        assert self._get_state()["tutor_mode_enabled"] is True

        off = self._set_mode(False)
        assert off["enabled"] is False
        assert off["state"]["tutor_mode_enabled"] is False
        assert self._get_state()["tutor_mode_enabled"] is False

    def test_update_tutor_state_partial(self):
        """PUT /api/chat/tutor/state applies a partial update and persists it."""
        response = self._put("chat/tutor/state", data={"scaffolding_level": 4}, json=True)
        self._assert_status_code_is_ok(response)
        assert response.json()["scaffolding_level"] == 4
        assert self._get_state()["scaffolding_level"] == 4

        # Restore the default so test ordering can't leak this value elsewhere.
        self._put("chat/tutor/state", data={"scaffolding_level": 3}, json=True)

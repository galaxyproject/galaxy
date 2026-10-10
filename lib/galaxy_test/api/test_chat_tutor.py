"""API tests for the cognitive tutor's learning-state endpoints and routing.

The learning-state endpoints are plain per-user preference CRUD (no LLM required),
so they run against any Galaxy with a logged-in user. The routing tests drive
``POST /api/chat`` for real and need agents configured; against the auto-started
test server that is the static backend, so they assert exact agent types.

## Running (auto-started server):
    ./run_tests.sh -api lib/galaxy_test/api/test_chat_tutor.py
"""

import json
from contextlib import contextmanager
from typing import Any
from unittest import SkipTest

from galaxy_test.base.decorators import requires_admin
from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_agents,
)
from ._framework import ApiTestCase

EXPECTED_STATE_KEYS = {
    "scaffolding_level",
    "interaction_count",
    "demonstrations_count",
    "tutor_mode_enabled",
    "last_interaction",
}

# Matching the fixture text exactly is what proves the tutor rule answered, not a fallback.
TUTOR_STATIC_REPLY = "Before I explain, what do you already know about this step?"


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
        assert "expertise_level" not in state
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

    def test_analytics_requires_admin(self):
        """The tutor analytics endpoint is admin-only."""
        response = self._get("chat/tutor/analytics", admin=False)
        self._assert_status_code_is(response, 403)

    @requires_admin
    def test_analytics_returns_aggregate_shape(self):
        """An admin can read aggregated tutor analytics (real queries run)."""
        response = self._get("chat/tutor/analytics", admin=True)
        self._assert_status_code_is_ok(response)
        data = response.json()
        for key in (
            "total_messages",
            "tutor_messages",
            "tutor_message_share",
            "tutor_feedback",
            "avg_conversation_length",
            "scaffolding_distribution",
            "total_demonstrations",
            "demonstrations_per_interaction",
        ):
            assert key in data


class TestChatTutorRoutingApi(ApiTestCase):
    """How POST /api/chat picks an agent when learning mode is involved."""

    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        config = self._get("configuration").json()
        self._registry_type = config.get("llm_registry_type", "default")
        self._require_tutor_agent()

    @property
    def _is_static(self) -> bool:
        return self._registry_type == "static"

    def _require_tutor_agent(self) -> None:
        # skip_without_agents only proves some LLM is configured; a deployment can still
        # disable the tutor, and then every exact routing assertion here is wrong.
        response = self._get("ai/agents")
        self._assert_status_code_is_ok(response)
        agent_types = [agent["agent_type"] for agent in response.json()["agents"]]
        if "teaching_assistant" not in agent_types:
            raise SkipTest("teaching_assistant agent is not enabled on this server")

    def _set_tutor_mode(self, enabled: bool) -> None:
        response = self._post("chat/tutor/mode", data={"enabled": enabled}, json=True)
        self._assert_status_code_is_ok(response)

    @contextmanager
    def _tutor_mode_on(self):
        # The session server and its user are shared across every API test module, so
        # learning mode has to come back off even when an assertion blows up.
        self._set_tutor_mode(True)
        try:
            yield
        finally:
            self._set_tutor_mode(False)

    def _chat_raw(
        self,
        query: str,
        agent_type: str = "auto",
        context: dict[str, Any] | None = None,
        job_id: str | None = None,
    ):
        url = f"chat?agent_type={agent_type}"
        if job_id is not None:
            url += f"&job_id={job_id}"
        payload: dict[str, Any] = {"query": query}
        if context is not None:
            payload["context"] = json.dumps(context)
        return self._post(url, payload, json=True)

    def _chat(self, query: str, **kwds) -> dict[str, Any]:
        response = self._chat_raw(query, **kwds)
        self._assert_status_code_is_ok(response)
        result = response.json()
        # The endpoint swallows agent failures into a 200 carrying error_code 500.
        assert result["error_code"] == 0, result["error_message"]
        return result

    def _responder(self, result: dict[str, Any]) -> str:
        agent_response = result.get("agent_response")
        assert agent_response, f"No agent_response in {result}"
        return agent_response["agent_type"]

    def _notebook_context(self, page_id: str, history_id: str | None = None) -> dict[str, Any]:
        context: dict[str, Any] = {"contextType": "notebook", "pageId": page_id}
        if history_id:
            context["historyId"] = history_id
        return context

    def _new_page(self, title: str) -> tuple[str, str]:
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content=f"# {title}")
        return page["id"], history_id

    def _tutor_message_count(self) -> int:
        response = self._get("chat/tutor/analytics", admin=True)
        self._assert_status_code_is_ok(response)
        return response.json()["tutor_messages"]

    @skip_without_agents
    def test_auto_query_reaches_tutor_when_learning_mode_is_on(self):
        with self._tutor_mode_on():
            result = self._chat("How do I trim adapters?")
        assert self._responder(result) == "teaching_assistant"
        if self._is_static:
            assert result["response"] == TUTOR_STATIC_REPLY

    @skip_without_agents
    def test_page_context_outranks_learning_mode_for_auto_queries(self):
        page_id, history_id = self._new_page("Page beats tutor")
        with self._tutor_mode_on():
            result = self._chat(
                "Summarize this for me",
                context=self._notebook_context(page_id, history_id),
            )
        assert self._responder(result) == "page_assistant"

    @skip_without_agents
    def test_auto_query_reaches_router_when_learning_mode_is_off(self):
        self._set_tutor_mode(False)
        result = self._chat("Tell me about Galaxy")
        assert self._responder(result) != "teaching_assistant"
        if self._is_static:
            assert self._responder(result) == "router"

    @skip_without_agents
    def test_explicit_tutor_request_keeps_the_tutor_despite_page_context(self):
        page_id, history_id = self._new_page("Explicit tutor")
        self._set_tutor_mode(False)
        result = self._chat(
            "Walk me through this",
            agent_type="teaching_assistant",
            context=self._notebook_context(page_id, history_id),
        )
        assert self._responder(result) == "teaching_assistant"

    @skip_without_agents
    @requires_admin
    def test_job_linked_tutor_chat_is_stored_and_counted(self):
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.new_dataset(history_id, content="1\n2\n3\n", wait=True)
        job_id = self.dataset_populator.get_history_dataset_details(history_id)["creating_job"]

        before = self._tutor_message_count()
        query = "Why does this upload have three lines?"
        with self._tutor_mode_on():
            result = self._chat(query, job_id=job_id)
        assert self._responder(result) == "teaching_assistant"
        assert result["exchange_id"]
        assert result["response"]
        after = self._tutor_message_count()
        if self._is_static:
            # Only the auto-started static server is quiet enough for an exact count.
            assert after == before + 1
        else:
            assert after >= before

        # A repeat POST for the same job replays the stored exchange instead of
        # re-running the agent, so it reads back what was persisted.
        cached = self._chat(query, job_id=job_id)
        assert self._responder(cached) == "teaching_assistant"
        assert cached["exchange_id"] == result["exchange_id"]
        assert cached["response"] == result["response"]

    @skip_without_agents
    def test_unreadable_page_id_leaves_auto_query_with_the_tutor(self):
        with self._tutor_mode_on():
            result = self._chat(
                "What should I look at next?",
                context=self._notebook_context("not-an-encoded-id"),
            )
        # A page hint the server can't decode is dropped rather than fatal, so routing
        # continues as if no page context had been sent at all.
        assert self._responder(result) == "teaching_assistant"

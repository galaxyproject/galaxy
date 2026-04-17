"""Integration tests for SSE-based history update notifications."""

import json
from urllib.parse import urljoin
from uuid import uuid4

import requests

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.base.sse import SSELineListener
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestHistorySSEIntegration(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_celery_tasks"] = False
        config["enable_sse_history_updates"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _events_stream_url(self) -> str:
        return urljoin(self.url, "api/events/stream")

    def _create_history(self, name=None) -> str:
        name = name or f"test_history_{uuid4()}"
        response = self._post("histories", data={"name": name}, json=True)
        self._assert_status_code_is_ok(response)
        return response.json()["id"]

    def test_history_update_contains_current_history_id(self):
        """The history_update event should contain the history's encoded ID."""
        history_id = self._create_history()

        listener = SSELineListener(self._events_stream_url(), self.galaxy_interactor.api_key)
        listener.start()
        try:
            self.dataset_populator.new_dataset(history_id, wait=False)
            history_events = listener.wait_for_event("history_update")
            found = any(history_id in json.loads(e["data"]).get("history_ids", []) for e in history_events)
            assert found, f"Expected history_id '{history_id}' in history_update events, got: {history_events}"
        finally:
            listener.stop()

    def test_history_update_is_scoped_to_owning_user(self):
        """User A must only see history_update events for their own histories.

        Inverted positive assertion: after user B's upload, user A uploads to
        their own history and we assert A's stream contains A's encoded id and
        not B's. This avoids a sleep-based "no events" test that was prone to
        flaking under slow CI.
        """
        user_b = self._setup_user(f"{uuid4()}@galaxy.test")
        _, user_b_api_key = self._setup_user_get_key(user_b["email"])

        user_a_history_id = self._create_history()

        listener = SSELineListener(self._events_stream_url(), self.galaxy_interactor.api_key)
        listener.start()
        try:
            # User B creates a history and uploads to it. User A must NOT see this.
            create_resp = requests.post(
                urljoin(self.url, "api/histories"),
                params={"key": user_b_api_key},
                json={"name": "User B History"},
            )
            assert create_resp.status_code == 200
            user_b_history_id = create_resp.json()["id"]

            requests.post(
                urljoin(self.url, f"api/histories/{user_b_history_id}/contents"),
                params={"key": user_b_api_key},
                json={"from_hda_id": None, "source": "pasted", "content": "user b content"},
            )

            # User A uploads to their own history — this is what A's stream must observe.
            self.dataset_populator.new_dataset(user_a_history_id, wait=False)
            history_events = listener.wait_for_event("history_update")
        finally:
            listener.stop()

        seen_ids: set[str] = set()
        for event in history_events:
            seen_ids.update(json.loads(event["data"]).get("history_ids", []))
        assert user_a_history_id in seen_ids, f"User A missed its own history_update: {history_events}"
        assert (
            user_b_history_id not in seen_ids
        ), f"User A received history_update for user B's history ({user_b_history_id}): {history_events}"

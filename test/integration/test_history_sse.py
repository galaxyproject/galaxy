"""Integration tests for SSE-based history update notifications."""

import json
from urllib.parse import urljoin
from uuid import uuid4

from galaxy.util.wait import wait_on
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.base.sse import (
    DEFAULT_WAIT_TIMEOUT,
    SSELineListener,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestHistorySSEIntegration(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_celery_tasks"] = False
        config["enable_sse_updates"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _events_stream_url(self) -> str:
        return urljoin(self.url, "api/events/stream")

    def _populator_for_user(self, api_key: str) -> DatasetPopulator:
        """Build a populator bound to a separate user so two users can act
        concurrently without context-switching the default interactor.
        """
        return DatasetPopulator(self._get_interactor(api_key=api_key))

    def test_history_update_contains_current_history_id(self):
        """The history_update event should contain the history's encoded ID."""
        history_id = self.dataset_populator.new_history(name=f"test_history_{uuid4()}")

        api_key = self.galaxy_interactor.api_key
        assert api_key is not None
        listener = SSELineListener(self._events_stream_url(), api_key)
        listener.start()
        try:
            self.dataset_populator.new_dataset(history_id, wait=False)
            history_events = listener.wait_for_event_where(
                "history_update",
                lambda e: history_id in json.loads(e["data"]).get("history_ids", []),
            )
            found = any(history_id in json.loads(e["data"]).get("history_ids", []) for e in history_events)
            assert found, f"Expected history_id '{history_id}' in history_update events, got: {history_events}"
        finally:
            listener.stop()

    def test_history_update_reaches_viewer_after_subscription(self):
        """After User A subscribes as a viewer of User B's history, A's SSE
        stream receives ``history_update`` events for that history. Without
        the subscription, A would only see events for histories they own.
        """
        user_b = self._setup_user(f"{uuid4()}@galaxy.test")
        _, user_b_api_key = self._setup_user_get_key(user_b["email"])
        user_b_populator = self._populator_for_user(user_b_api_key)

        # User B creates a history that A will watch as a viewer.
        user_b_history_id = user_b_populator.new_history(name="User B History")

        api_key = self.galaxy_interactor.api_key
        assert api_key is not None
        listener = SSELineListener(self._events_stream_url(), api_key)
        listener.start()
        try:
            # User A subscribes as a viewer for User B's history.
            sub_resp = self._post(
                "events/history-subscriptions",
                data={"history_ids": [user_b_history_id]},
                json=True,
            )
            self._assert_status_code_is(sub_resp, 204)

            # User B mutates their own history. A must see the SSE event for it.
            user_b_populator.new_dataset(user_b_history_id, content="viewer test", wait=False)
            history_events = listener.wait_for_event_where(
                "history_update",
                lambda e: user_b_history_id in json.loads(e["data"]).get("history_ids", []),
            )
            assert any(
                user_b_history_id in json.loads(e["data"]).get("history_ids", []) for e in history_events
            ), f"Viewer subscription did not deliver history_update: {history_events}"

            # Unsubscribe and confirm subsequent mutations no longer arrive.
            unsub_resp = self._delete(
                "events/history-subscriptions",
                data={"history_ids": [user_b_history_id]},
                json=True,
            )
            self._assert_status_code_is(unsub_resp, 204)

            # The unsubscribe is applied asynchronously by the control queue,
            # whose single consumer can lag by seconds (e.g. while it runs the
            # startup toolbox search index rebuild), and B's first upload job
            # keeps changing B's history, so events for B dispatched before
            # the DELETE can still reach A after it returns. Control tasks are
            # consumed in order: once an event for
            # A's own history mutated after the DELETE arrives, the unsubscribe
            # has been applied and every earlier event has been delivered.
            user_a_history_id = self.dataset_populator.new_history(name=f"test_history_{uuid4()}")

            def is_user_a_event(e):
                return user_a_history_id in json.loads(e["data"]).get("history_ids", [])

            self.dataset_populator.new_dataset(user_a_history_id, wait=False)
            listener.wait_for_event_where("history_update", is_user_a_event)
            baseline_count = len(listener.get_events("history_update"))

            # Mutate B's history again, and prove no events for it land within
            # the wait window — driven by waiting for a new event for A's *own*
            # history (positive assertion to avoid sleep-based flakes), then
            # asserting B's id is absent.
            user_b_populator.new_dataset(user_b_history_id, content="post-unsubscribe", wait=False)
            self.dataset_populator.new_dataset(user_a_history_id, wait=False)

            def new_user_a_events():
                events = listener.get_events("history_update")[baseline_count:]
                return events if any(is_user_a_event(e) for e in events) else None

            after_events = wait_on(new_user_a_events, "new history_update for User A's history", DEFAULT_WAIT_TIMEOUT)
            seen_b_after_unsub = any(
                user_b_history_id in json.loads(e["data"]).get("history_ids", []) for e in after_events
            )
            assert (
                not seen_b_after_unsub
            ), f"User A still received history_update events for User B's history after unsubscribing: {after_events}"
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
        user_b_populator = self._populator_for_user(user_b_api_key)

        user_a_history_id = self.dataset_populator.new_history(name=f"test_history_{uuid4()}")

        api_key = self.galaxy_interactor.api_key
        assert api_key is not None
        listener = SSELineListener(self._events_stream_url(), api_key)
        listener.start()
        try:
            # User B creates a history and uploads to it. User A must NOT see this.
            user_b_history_id = user_b_populator.new_history(name="User B History")
            user_b_populator.new_dataset(user_b_history_id, content="user b content", wait=False)

            # User A uploads to their own history — this is what A's stream must observe.
            self.dataset_populator.new_dataset(user_a_history_id, wait=False)
            history_events = listener.wait_for_event_where(
                "history_update",
                lambda e: user_a_history_id in json.loads(e["data"]).get("history_ids", []),
            )
        finally:
            listener.stop()

        seen_ids: set[str] = set()
        for event in history_events:
            seen_ids.update(json.loads(event["data"]).get("history_ids", []))
        assert user_a_history_id in seen_ids, f"User A missed its own history_update: {history_events}"
        assert (
            user_b_history_id not in seen_ids
        ), f"User A received history_update for user B's history ({user_b_history_id}): {history_events}"

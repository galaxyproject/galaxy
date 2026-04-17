"""Integration tests for the notification SSE (Server-Sent Events) endpoint."""

import json
from typing import Optional
from urllib.parse import urljoin
from uuid import uuid4

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.base.sse import SSELineListener
from galaxy_test.driver.integration_util import IntegrationTestCase


def notification_test_data(subject: Optional[str] = None, message: Optional[str] = None) -> dict:
    return {
        "source": "integration_tests",
        "variant": "info",
        "category": "message",
        "content": {
            "category": "message",
            "subject": subject or "Testing Subject",
            "message": message or "Testing Message",
        },
    }


def notification_broadcast_test_data(subject: Optional[str] = None, message: Optional[str] = None) -> dict:
    return {
        "source": "integration_tests",
        "variant": "info",
        "category": "broadcast",
        "content": {
            "category": "broadcast",
            "subject": subject or "Testing Broadcast Subject",
            "message": message or "Testing Broadcast Message",
        },
    }


def _notification_subjects(events: list[dict]) -> list[str]:
    """Extract ``content.subject`` from each SSE ``data`` payload.

    Verifies JSON shape rather than substring-matching raw ``data`` strings — a
    regression in the envelope (missing id, wrong serializer, content key
    renamed) fails here instead of silently passing. Each ``data`` payload is
    a ``NotificationResponse`` dump with a top-level ``content.subject``.
    """
    subjects = []
    for event in events:
        payload = json.loads(event["data"])
        subjects.append(payload["content"]["subject"])
    return subjects


class TestNotificationSSEIntegration(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = False

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_celery_tasks"] = False
        config["enable_notification_system"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _stream_url(self) -> str:
        return urljoin(self.url, "api/notifications/stream")

    def test_sse_receives_notification_events(self):
        """When a notification is created, the SSE stream should receive it."""
        user = self._setup_user(f"{uuid4()}@galaxy.test")
        _, user_api_key = self._setup_user_get_key(user["email"])

        listener = SSELineListener(self._stream_url(), user_api_key)
        listener.start()
        try:
            subject = f"sse_test_{uuid4()}"
            request = {
                "recipients": {"user_ids": [user["id"]]},
                "notification": notification_test_data(subject=subject, message="SSE test notification"),
            }
            response = self._post("notifications", data=request, admin=True, json=True)
            self._assert_status_code_is_ok(response)

            notification_events = listener.wait_for_event("notification_update")
        finally:
            listener.stop()

        assert subject in _notification_subjects(
            notification_events
        ), f"Expected subject '{subject}' in SSE events, got: {notification_events}"

    def test_sse_receives_broadcast_events(self):
        """When a broadcast is created, the SSE stream should receive it."""
        listener = SSELineListener(self._stream_url(), self.galaxy_interactor.api_key)
        listener.start()
        try:
            subject = f"broadcast_sse_test_{uuid4()}"
            payload = notification_broadcast_test_data(subject=subject)
            response = self._post("notifications/broadcast", data=payload, admin=True, json=True)
            self._assert_status_code_is_ok(response)

            broadcast_events = listener.wait_for_event("broadcast_update")
        finally:
            listener.stop()

        # Broadcast events carry a BroadcastNotificationResponse, which shares
        # the top-level content.subject shape with per-user notifications.
        broadcast_subjects = [json.loads(e["data"])["content"]["subject"] for e in broadcast_events]
        assert subject in broadcast_subjects, f"Expected subject '{subject}' in broadcast events: {broadcast_events}"

    def test_sse_catchup_on_reconnect(self):
        """Reconnecting with Last-Event-ID should replay a catch-up notification_status event.

        The ``Last-Event-ID`` value is the server-issued ID from a prior event,
        not a client-side timestamp. This avoids clock-skew flake between the
        test runner and the app in containerized CI.
        """
        user = self._setup_user(f"{uuid4()}@galaxy.test")
        _, user_api_key = self._setup_user_get_key(user["email"])

        # First connection: capture the server-issued event id of the first notification.
        listener_1 = SSELineListener(self._stream_url(), user_api_key)
        listener_1.start()
        try:
            subject_1 = f"first_{uuid4()}"
            request = {
                "recipients": {"user_ids": [user["id"]]},
                "notification": notification_test_data(subject=subject_1),
            }
            response = self._post("notifications", data=request, admin=True, json=True)
            self._assert_status_code_is_ok(response)
            first_events = listener_1.wait_for_event("notification_update")
        finally:
            listener_1.stop()

        last_event_id = next((e["id"] for e in first_events if e.get("id")), None)
        assert last_event_id, f"No server-issued id on first notification event: {first_events}"

        # Emit a second notification while disconnected; it should appear in the catch-up.
        subject_2 = f"catchup_{uuid4()}"
        request = {
            "recipients": {"user_ids": [user["id"]]},
            "notification": notification_test_data(subject=subject_2, message="Catch-up test"),
        }
        response = self._post("notifications", data=request, admin=True, json=True)
        self._assert_status_code_is_ok(response)

        # Reconnect with Last-Event-ID = the captured id. The catch-up must include
        # the notification sent after that id but not the one that produced it.
        listener_2 = SSELineListener(
            self._stream_url(),
            user_api_key,
            headers={"Last-Event-ID": last_event_id},
        )
        listener_2.start()
        try:
            status_events = listener_2.wait_for_event("notification_status")
        finally:
            listener_2.stop()

        replayed_subjects: list[str] = []
        for event in status_events:
            payload = json.loads(event["data"])
            replayed_subjects.extend(n["content"]["subject"] for n in payload.get("notifications", []))
        assert subject_2 in replayed_subjects, f"Missed catch-up of '{subject_2}': {status_events}"
        assert (
            subject_1 not in replayed_subjects
        ), f"Last-Event-ID did not filter — '{subject_1}' replayed: {status_events}"

"""Playwright E2E test for the notification SSE pipeline.

Verifies that when an admin creates a notification via the API,
a logged-in user sees it appear in the UI in real-time (within seconds)
without a page refresh, proving the SSE push pipeline works end-to-end.
"""

from uuid import uuid4

from galaxy.util.wait import wait_on
from galaxy_test.selenium.framework import (
    managed_history,
    selenium_test,
)
from .framework import SeleniumIntegrationTestCase

SSE_CONNECT_TIMEOUT_SECONDS = 15
SSE_EVENT_TIMEOUT_SECONDS = 15


class TestNotificationSSESeleniumIntegration(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_celery_tasks"] = False

    def _wait_for_sse_connected(self) -> None:
        """Block until the frontend confirms the SSE pipeline is live.

        Without this gate, the 30 s polling fallback silently masks a broken
        SSE pipeline — the UI would still update, but via polling, and the
        test would falsely pass.
        """
        wait_on(
            lambda: True if self.driver.execute_script("return window.__galaxy_sse_connected === true") else None,
            "window.__galaxy_sse_connected === true",
            timeout=SSE_CONNECT_TIMEOUT_SECONDS,
        )

    def _last_sse_event_ts(self) -> int:
        """Return the last SSE event timestamp recorded by the composable, or 0."""
        return self.driver.execute_script("return window.__galaxy_sse_last_event_ts || 0") or 0

    def _wait_for_sse_event_after(self, baseline_ts: int) -> None:
        """Block until an SSE event arrives after ``baseline_ts``.

        Guards against a silent regression where the UI update originates from
        the polling fallback rather than the SSE push: ``__galaxy_sse_last_event_ts``
        only advances when the composable's event listener fires.
        """
        wait_on(
            lambda: True if self._last_sse_event_ts() > baseline_ts else None,
            "window.__galaxy_sse_last_event_ts advanced past baseline",
            timeout=SSE_EVENT_TIMEOUT_SECONDS,
        )

    @selenium_test
    @managed_history
    def test_notification_appears_via_sse(self):
        """Send a notification via the API and verify it appears in the UI without refresh."""
        # Get the logged-in user's info so we can send a notification to them
        user_info = self._get("users/current").json()
        user_id = user_info["id"]

        # Navigate to notifications page so the store is watching
        self.driver.get(f"{self.target_url_from_selenium}/user/notifications")
        self._wait_for_sse_connected()
        baseline_ts = self._last_sse_event_ts()
        self.screenshot("notification_sse_before")

        # Send a notification to this user via the admin API
        subject = f"SSE E2E Test {uuid4()}"
        notification_request = {
            "recipients": {"user_ids": [user_id]},
            "notification": {
                "source": "integration_tests",
                "variant": "info",
                "category": "message",
                "content": {
                    "category": "message",
                    "subject": subject,
                    "message": "This notification was pushed via SSE",
                },
            },
        }
        response = self._post("notifications", data=notification_request, admin=True, json=True)
        self._assert_status_code_is_ok(response)

        # Prove the incoming update arrived via SSE: the event-timestamp hook
        # only advances when useSSE's listener fires. If this times out while
        # the UI still shows the notification, polling picked it up — a silent
        # regression this assertion catches.
        self._wait_for_sse_event_after(baseline_ts)
        self.wait_for_selector_visible(f"text={subject}", timeout=SSE_EVENT_TIMEOUT_SECONDS * 1000)
        self.screenshot("notification_sse_after")

    @selenium_test
    @managed_history
    def test_notification_bell_updates_via_sse(self):
        """The notification bell indicator should update when a new notification arrives via SSE."""
        user_info = self._get("users/current").json()
        user_id = user_info["id"]

        # Go to home page (bell is in masthead)
        self.home()
        self._wait_for_sse_connected()
        baseline_ts = self._last_sse_event_ts()

        # Send a notification
        subject = f"Bell Test {uuid4()}"
        notification_request = {
            "recipients": {"user_ids": [user_id]},
            "notification": {
                "source": "integration_tests",
                "variant": "info",
                "category": "message",
                "content": {
                    "category": "message",
                    "subject": subject,
                    "message": "Testing bell indicator update via SSE",
                },
            },
        }
        response = self._post("notifications", data=notification_request, admin=True, json=True)
        self._assert_status_code_is_ok(response)

        self._wait_for_sse_event_after(baseline_ts)
        # The indicator dot should appear on the bell (within the #activity-notifications element)
        self.wait_for_selector_visible("#activity-notifications .indicator", timeout=SSE_EVENT_TIMEOUT_SECONDS * 1000)
        self.screenshot("notification_bell_indicator")

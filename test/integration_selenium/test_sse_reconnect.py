"""Playwright E2E test for the SSE managed-reconnect path.

The browser's native ``EventSource`` retry gives up once it sees a non-event
stream response (typical for a 429 or 5xx fronted by a load balancer that
serves an HTML error page); the composable in
``client/src/composables/useNotificationSSE.ts`` notices that ``readyState``
flips to ``CLOSED`` and reopens the stream with full-jitter exponential
backoff. This test fails the first request to ``/api/events/stream`` with a
503, then lets subsequent requests through, and asserts:

1. The frontend's reconnect-attempts global advances (proving we went through
   the managed path, not the native loop).
2. The stream comes back up (``window.__galaxy_sse_connected``).
3. Events delivered on the *new* stream actually fire the SSE listener — a
   regression test for the case where the EventSource reconnects but the
   per-event-type dispatchers were lost.

Failure injection is browser-side via ``page.route()`` so no production server
code carries a test-only disconnect primitive.
"""

from uuid import uuid4

from galaxy.util.wait import wait_on
from galaxy_test.selenium.framework import (
    managed_history,
    playwright_only,
    selenium_test,
)
from .framework import SeleniumIntegrationTestCase

SSE_CONNECT_TIMEOUT_SECONDS = 30
SSE_EVENT_TIMEOUT_SECONDS = 15


class TestSSEReconnectSeleniumIntegration(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # Mirrors test_notification_sse.py — the SSE pipeline is only enabled
        # when both notifications and the SSE flag are on, and Celery is
        # disabled so notification dispatch goes through the synchronous path
        # the test asserts on.
        config["enable_notification_system"] = True
        config["enable_sse_updates"] = True
        config["enable_celery_tasks"] = False

    def _wait_for_sse_connected(self) -> None:
        wait_on(
            lambda: True if self.execute_script("return window.__galaxy_sse_connected === true") else None,
            "window.__galaxy_sse_connected === true",
            timeout=SSE_CONNECT_TIMEOUT_SECONDS,
        )

    def _last_sse_event_ts(self) -> int:
        return self.execute_script("return window.__galaxy_sse_last_event_ts || 0") or 0

    def _wait_for_sse_event_after(self, baseline_ts: int) -> None:
        wait_on(
            lambda: True if self._last_sse_event_ts() > baseline_ts else None,
            "window.__galaxy_sse_last_event_ts advanced past baseline",
            timeout=SSE_EVENT_TIMEOUT_SECONDS,
        )

    def _reconnect_attempts(self) -> int:
        return self.execute_script("return window.__galaxy_sse_reconnect_attempts || 0") or 0

    @selenium_test
    @managed_history
    @playwright_only("Uses Playwright page.route() to fail the SSE endpoint with a transient 503.")
    def test_client_reconnects_after_transient_503(self) -> None:
        """Force a 503 on the first SSE request, then assert reconnect + event delivery."""
        # Resolve the browser's logged-in user (the Selenium-registered one)
        # — same caveat as test_notification_sse.py: the API interactor's
        # default-user key is a different user, so the SSE push must target
        # the user attached to the browser cookie.
        user_info = self.api_get("users/current")
        user_id = user_info["id"]

        # Arm a one-shot 503 BEFORE navigating so the route is in place the
        # moment the page opens its EventSource. ``served`` is closed over so
        # only the first matching request is intercepted; subsequent attempts
        # (the actual reconnect) hit the real Galaxy endpoint.
        served = {"v": False}

        def handle_route(route, request):
            if not served["v"]:
                served["v"] = True
                # 503 is in client-side RETRYABLE_STATUSES; the response has
                # no text/event-stream body, which makes EventSource flip to
                # readyState=CLOSED — exactly the path the managed reconnect
                # handler covers.
                route.fulfill(
                    status=503,
                    headers={"Content-Type": "text/plain"},
                    body="overloaded",
                )
            else:
                route.continue_()

        self.page.route("**/api/events/stream", handle_route)

        # Navigate to a page that subscribes to the SSE pipeline.
        self.get("user/notifications")

        # Connection must come up via the managed reconnect path. The first
        # attempt is failed by the route above; the composable's onerror sees
        # readyState=CLOSED, increments __galaxy_sse_reconnect_attempts, and
        # schedules a reopen at backoff in [500ms, 1500ms). 30s budget covers
        # ample time for navigation + reconnect on a slow CI runner.
        self._wait_for_sse_connected()

        # Prove the connection arrived via reconnect, not on the first try —
        # if the route hadn't fired (or 503 hadn't been treated as a fatal
        # error by EventSource), the counter would still be 0.
        attempts_after_reconnect = self._reconnect_attempts()
        assert (
            attempts_after_reconnect >= 1
        ), f"expected at least one managed reconnect after a 503, got {attempts_after_reconnect}"
        assert served["v"], "the route handler never fired — Playwright did not intercept the SSE request"
        self.screenshot("sse_reconnect_connected")

        # Now push a notification to the browser-logged-in user. The event
        # must arrive on the *reconnected* stream (the original was killed
        # by the 503), exercising the dispatcher re-registration in the
        # reconnect path.
        baseline_ts = self._last_sse_event_ts()
        subject = f"SSE Reconnect Test {uuid4()}"
        notification_request = {
            "recipients": {"user_ids": [user_id]},
            "notification": {
                "source": "integration_tests",
                "variant": "info",
                "category": "message",
                "content": {
                    "category": "message",
                    "subject": subject,
                    "message": "Delivered after a transient 503 + managed reconnect",
                },
            },
        }
        response = self._post("notifications", data=notification_request, admin=True, json=True)
        self._assert_status_code_is_ok(response)

        # Timestamp only advances when the SSE listener fires — distinguishes
        # SSE delivery from the polling fallback even in this reconnect path.
        self._wait_for_sse_event_after(baseline_ts)
        self.wait_for_xpath_visible(f'//*[contains(text(), "{subject}")]', timeout=SSE_EVENT_TIMEOUT_SECONDS)
        self.screenshot("sse_reconnect_event_delivered")

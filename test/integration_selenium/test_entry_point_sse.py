"""Playwright E2E test for the interactive-tool entry-point SSE pipeline.

Verifies that when an interactive-tool entry point transitions to ``configured``
server-side (the runner's port-routing hook calls ``configure_entry_points``),
a logged-in user's browser receives the ``entry_point_update`` SSE event and
the entry-point store refetches, without the 10 s polling interval.

This test stubs the server-side runner callback: it creates the Job and entry
point directly and calls ``InteractiveToolManager.configure_entry_points`` on
the live app. That invocation is the exact dispatch site in production.
"""

from uuid import uuid4

from galaxy.model import (
    InteractiveToolEntryPoint,
    Job,
)
from galaxy.util.wait import wait_on
from galaxy_test.selenium.framework import (
    managed_history,
    selenium_test,
)
from .framework import SeleniumIntegrationTestCase

SSE_CONNECT_TIMEOUT_SECONDS = 15
SSE_EVENT_TIMEOUT_SECONDS = 15


class TestEntryPointSSESeleniumIntegration(SeleniumIntegrationTestCase):
    ensure_registered = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_celery_tasks"] = False
        # App.vue only calls entryPointStore.startWatchingEntryPoints() when
        # interactivetools_enable is True, and the store only opens an SSE
        # connection when enable_sse_updates is True. Without both,
        # __galaxy_sse_connected never becomes true and the gate below times out.
        config["interactivetools_enable"] = True
        config["enable_sse_updates"] = True

    def _wait_for_sse_connected(self) -> None:
        """Block until the frontend confirms the SSE pipeline is live."""
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

    def _create_it_job_with_entry_point(self, tool_port: int = 8888) -> tuple[int, int]:
        # Use the browser's cookie-authenticated user, not the API interactor's
        # default: SSE connects under the Selenium-registered user, and the
        # dispatch's user_id must match or push_to_user finds no queues.
        user_info = self.api_get("users/current")
        user_id = self._decode_id(user_info["id"])
        sa_session = self._app.model.context
        job = Job()
        job.user_id = user_id
        job.tool_id = "interactivetool_simple"
        job.state = Job.states.RUNNING
        sa_session.add(job)
        sa_session.flush()
        ep = InteractiveToolEntryPoint(
            job=job,
            tool_port=tool_port,
            entry_url="/",
            name=f"selenium entry {uuid4()}",
            label="selenium",
            requires_domain=True,
            requires_path_in_url=False,
            requires_path_in_header_named=None,
        )
        sa_session.add(ep)
        sa_session.commit()
        return job.id, ep.id

    @selenium_test
    @managed_history
    def test_entry_point_update_pushed_via_sse(self):
        """configure_entry_points should trigger an SSE push the client observes."""
        # Navigate home so the entry-point store is mounted and subscribed.
        self.home()
        self._wait_for_sse_connected()
        baseline_ts = self._last_sse_event_ts()
        self.screenshot("entry_point_sse_before")

        job_id, _ep_id = self._create_it_job_with_entry_point(tool_port=8888)

        # Stub the runner hook: call configure_entry_points on the live app.
        sa_session = self._app.model.context
        job = sa_session.get(Job, job_id)
        assert job is not None
        self._app.interactivetool_manager.configure_entry_points(
            job,
            {"8888": {"host": "host.invalid", "port": 12345, "protocol": "http"}},
        )

        # Prove the update arrived via SSE (not polling): the composable's
        # event-timestamp hook only advances when useSSE's listener fires.
        self._wait_for_sse_event_after(baseline_ts)
        self.screenshot("entry_point_sse_after")

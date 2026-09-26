"""Integration tests for SSE-based interactive-tool entry-point update notifications.

Mirrors ``test_history_sse.py``. Rather than spin up a real containerized
interactive tool (which would require docker), these tests exercise the
dispatch path by creating a ``Job`` and ``InteractiveToolEntryPoint`` rows
directly via the live app's SQLAlchemy session and invoking
``InteractiveToolManager.configure_entry_points`` with a stub ``ports_dict``.
This is exactly the moment the event fires in production — the job runner's
port-routing hook is the only upstream caller, and the SSE dispatch happens
after the DB commit regardless of how the ports were obtained.
"""

import time
from urllib.parse import urljoin
from uuid import uuid4

from galaxy.model import (
    InteractiveToolEntryPoint,
    Job,
)
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.base.sse import SSELineListener
from galaxy_test.driver.integration_util import IntegrationTestCase


def _make_ports_dict(tool_port: int) -> dict:
    """Stub the runner's port-routing payload — one tool_port, fake host/proto."""
    return {
        str(tool_port): {
            "host": "host.invalid",
            "port": 12345,
            "protocol": "http",
        }
    }


class TestEntryPointSSEIntegration(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_celery_tasks"] = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _events_stream_url(self) -> str:
        return urljoin(self.url, "api/events/stream")

    def _create_it_job_with_entry_point(self, user_id: int, tool_port: int = 8888) -> tuple[int, int]:
        """Create a minimal Job + unconfigured InteractiveToolEntryPoint row pair.

        Returns ``(job_id, entry_point_id)``. The session used is the live
        app's; the rows are real and survive the call.
        """
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
            name="test entry point",
            label="test",
            requires_domain=True,
            requires_path_in_url=False,
            requires_path_in_header_named=None,
        )
        sa_session.add(ep)
        sa_session.commit()
        return job.id, ep.id

    def test_entry_point_update_event_fires_on_configure(self):
        """configure_entry_points should fire an ``entry_point_update`` wake-up event."""
        api_key = self.galaxy_interactor.api_key
        assert api_key is not None
        user_id = self._user_id_for_api_key(api_key)
        job_id, _ = self._create_it_job_with_entry_point(user_id)

        listener = SSELineListener(self._events_stream_url(), api_key)
        listener.start()
        try:
            sa_session = self._app.model.context
            job = sa_session.get(Job, job_id)
            assert job is not None
            self._app.interactivetool_manager.configure_entry_points(job, _make_ports_dict(8888))

            entry_point_events = listener.wait_for_event("entry_point_update")
        finally:
            listener.stop()

        # The event carries no payload: the client refetches ``/api/entry_points``
        # (the canonical source) on receipt, so the event just needs to arrive.
        assert len(entry_point_events) >= 1, f"Expected entry_point_update wake-up, got: {entry_point_events}"
        assert entry_point_events[0]["event"] == "entry_point_update"

    def test_entry_point_update_is_scoped_to_owning_user(self):
        """User A must not see entry_point_update events for user B's jobs.

        The event has no payload to cross-check with, so we assert on event
        count: user A's stream should receive exactly one event for its own
        ``configure_entry_points`` call and none for user B's.
        """
        user_b = self._setup_user(f"{uuid4()}@galaxy.test")
        _, user_b_api_key = self._setup_user_get_key(user_b["email"])
        user_b_id = self._user_id_for_api_key(user_b_api_key)

        user_a_api_key = self.galaxy_interactor.api_key
        assert user_a_api_key is not None
        user_a_id = self._user_id_for_api_key(user_a_api_key)

        job_a_id, _ = self._create_it_job_with_entry_point(user_a_id, tool_port=7001)
        job_b_id, _ = self._create_it_job_with_entry_point(user_b_id, tool_port=7002)

        listener = SSELineListener(self._events_stream_url(), user_a_api_key)
        listener.start()
        try:
            sa_session = self._app.model.context
            job_b = sa_session.get(Job, job_b_id)
            assert job_b is not None
            # User B's job — user A must NOT see this.
            self._app.interactivetool_manager.configure_entry_points(job_b, _make_ports_dict(7002))
            # Give the broker a moment so a leaked event (if any) would arrive
            # before we fire user A's event — the assertion would then catch
            # more than one event on user A's stream.
            time.sleep(0.5)

            job_a = sa_session.get(Job, job_a_id)
            assert job_a is not None
            # User A's own job — this is what A's stream must observe.
            self._app.interactivetool_manager.configure_entry_points(job_a, _make_ports_dict(7001))

            entry_point_events = listener.wait_for_event("entry_point_update")
        finally:
            listener.stop()

        assert (
            len(entry_point_events) == 1
        ), f"User A expected exactly one entry_point_update (own job); saw {len(entry_point_events)}: {entry_point_events}"

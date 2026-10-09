"""Unit tests for the per-worker SSE connection-count gauge.

``SSEConnectionManager.emit_connection_gauges`` is sampled inside each web
worker (the only process that holds its connections), so these tests assert it
reports the manager's *own* counts, tags each series with ``server_name`` so
per-worker series don't collide, and no-ops without a statsd client.
``SSEConnectionGaugeEmitter`` is the daemon-thread driver; we check it emits at
least once and stops cleanly.
"""

import threading
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    cast,
)

from galaxy.managers.sse import (
    SSEConnectionGaugeEmitter,
    SSEConnectionManager,
)
from galaxy.web.statsd_client import VanillaGalaxyStatsdClient


@dataclass
class FakeStatsdClient:
    """In-memory recorder — captures ``gauge`` calls as plain data.

    ``recorded`` fires on every ``gauge`` call so a test can wait on the real
    effect (a gauge landed) without instrumenting the production code.
    """

    gauges: list[tuple[str, float, tuple[tuple[str, str], ...]]] = field(default_factory=list)
    recorded: threading.Event = field(default_factory=threading.Event)

    def gauge(self, metric: str, value: float, tags: dict[str, str] | None = None) -> None:
        self.gauges.append((metric, value, tuple(sorted((tags or {}).items()))))
        self.recorded.set()

    def gauges_for(self, metric: str) -> list[tuple[float, dict[str, str]]]:
        return [(v, dict(t)) for m, v, t in self.gauges if m == metric]


def _manager(statsd: FakeStatsdClient | None) -> SSEConnectionManager:
    return SSEConnectionManager(statsd_client=cast(VanillaGalaxyStatsdClient | None, statsd))


async def test_emit_connection_gauges_reports_own_counts_tagged_by_server_name():
    statsd = FakeStatsdClient()
    manager = _manager(statsd)
    # Two connections for a logged-in user, one anonymous (session-only).
    manager.connect(user_id=7)
    manager.connect(user_id=7)
    manager.connect(user_id=None, galaxy_session_id=99)

    manager.emit_connection_gauges("main.1")

    assert statsd.gauges_for("galaxy.sse.connections.active") == [
        (3, {"kind": "broadcast", "server_name": "main.1"}),
        (2, {"kind": "per_user", "server_name": "main.1"}),
    ]


async def test_emit_connection_gauges_is_noop_without_statsd():
    manager = _manager(None)
    manager.connect(user_id=1)
    # Must not raise even though no statsd client is configured.
    manager.emit_connection_gauges("main.1")


async def test_emitter_emits_then_stops():
    statsd = FakeStatsdClient()
    manager = _manager(statsd)
    manager.connect(user_id=1)

    # interval=600 so the thread emits once then blocks until shutdown; we wait
    # on the recorder's event (the real effect) rather than patching the manager.
    emitter = SSEConnectionGaugeEmitter(manager, "main.1", interval=600)
    emitter.start()
    try:
        assert statsd.recorded.wait(timeout=5), "emitter never emitted a gauge"
    finally:
        emitter.shutdown()
        emitter.join(timeout=5)
    assert not emitter.is_alive()
    assert statsd.gauges_for("galaxy.sse.connections.active")

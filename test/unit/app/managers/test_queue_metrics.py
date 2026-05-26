"""Unit tests for :mod:`galaxy.managers.queue_metrics`.

The ``SSEConnectionManager`` and the kombu connection are small hand-built
fakes — no broker or database is required. Assertions are on the recorded
state of the statsd client (counters, timings) rather than on mock call-lists
so a regression that stops emitting a gauge fails the test for the right
reason.

The failure-isolation test drives real sub-emitters into their error paths by
handing them genuinely broken collaborators (a connection whose ``clone()``
raises, a model whose ``new_session()`` raises). That way the test exercises
the real ``_run`` wrapper rather than asserting a monkey-patched side_effect.
"""

from dataclasses import (
    dataclass,
    field,
)
from types import SimpleNamespace
from typing import (
    cast,
    Optional,
)
from unittest.mock import MagicMock

import pytest

from galaxy.managers import queue_metrics
from galaxy.managers.sse import SSEConnectionManager
from galaxy.model.mapping import GalaxyModelMapping
from galaxy.web.statsd_client import VanillaGalaxyStatsdClient
from galaxy.web_stack import ApplicationStack

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class FakeStatsdClient:
    """In-memory statsd recorder — see docstring in ``test_sse_dispatch.py``."""

    counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = field(default_factory=dict)
    timings: list[tuple[str, float, tuple[tuple[str, str], ...]]] = field(default_factory=list)

    def incr(self, metric: str, tags: Optional[dict[str, str]] = None) -> None:
        key = (metric, tuple(sorted((tags or {}).items())))
        self.counters[key] = self.counters.get(key, 0) + 1

    def timing(self, metric: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        self.timings.append((metric, value, tuple(sorted((tags or {}).items()))))

    def counter(self, metric: str, tags: Optional[dict[str, str]] = None) -> int:
        return self.counters.get((metric, tuple(sorted((tags or {}).items()))), 0)

    def timings_for(self, metric: str) -> list[tuple[float, dict[str, str]]]:
        return [(v, dict(t)) for m, v, t in self.timings if m == metric]


def _fake_sse_manager(broadcast: int = 3, per_user: int = 5):
    m = MagicMock(spec=SSEConnectionManager)
    m.total_broadcast_connections = broadcast
    m.total_per_user_connections = per_user
    return m


def _make_fake_queue(name: str, count: int):
    """Fake kombu Queue exposing ``.bind(channel).queue_declare(passive=True).message_count``."""
    declared = SimpleNamespace(message_count=count)
    bound = SimpleNamespace(queue_declare=lambda passive: declared)
    return SimpleNamespace(name=name, bind=lambda channel: bound)


def _make_fake_connection(channel=None):
    """Fake kombu Connection whose ``.clone()`` is usable as a context manager."""
    channel = channel or MagicMock()
    conn_cm = MagicMock()
    conn_cm.channel.return_value = channel
    cm = MagicMock()
    cm.__enter__ = lambda self: conn_cm
    cm.__exit__ = lambda self, *a: False
    connection = MagicMock()
    connection.clone.return_value = cm
    return connection


# ---------------------------------------------------------------------------
# Sub-emitter tests — assert on recorded state
# ---------------------------------------------------------------------------


def test_emit_sse_connection_gauges_emits_both_kinds():
    statsd = FakeStatsdClient()
    queue_metrics.emit_sse_connection_gauges(
        cast(VanillaGalaxyStatsdClient, statsd), _fake_sse_manager(broadcast=4, per_user=7)
    )

    assert statsd.timings_for("galaxy.sse.connections.active") == [
        (4, {"kind": "broadcast"}),
        (7, {"kind": "per_user"}),
    ]


def test_emit_control_queue_depth_emits_per_queue(monkeypatch):
    statsd = FakeStatsdClient()
    fake_queues = [
        _make_fake_queue("control.main@h", 3),
        _make_fake_queue("control.main.1@h", 0),
    ]
    monkeypatch.setattr(
        queue_metrics,
        "all_control_queues_for_declare",
        lambda application_stack: fake_queues,
    )

    queue_metrics.emit_control_queue_depth(
        cast(VanillaGalaxyStatsdClient, statsd),
        _make_fake_connection(),
        cast(ApplicationStack, MagicMock()),
    )

    assert statsd.timings_for("galaxy.control_queue.depth") == [
        (3, {"queue_name": "control.main@h"}),
        (0, {"queue_name": "control.main.1@h"}),
    ]


def test_emit_control_queue_depth_skips_failed_passive_declare(monkeypatch):
    """One bad queue → we skip it and keep going for the rest."""
    statsd = FakeStatsdClient()

    def bad_declare(passive):
        raise RuntimeError("queue does not exist yet")

    good_queue = _make_fake_queue("control.good@h", 9)
    bad_queue = SimpleNamespace(
        name="control.bad@h",
        bind=lambda channel: SimpleNamespace(queue_declare=bad_declare),
    )
    monkeypatch.setattr(queue_metrics, "all_control_queues_for_declare", lambda stack: [good_queue, bad_queue])

    queue_metrics.emit_control_queue_depth(
        cast(VanillaGalaxyStatsdClient, statsd),
        _make_fake_connection(),
        cast(ApplicationStack, MagicMock()),
    )

    assert statsd.timings_for("galaxy.control_queue.depth") == [
        (9, {"queue_name": "control.good@h"}),
    ]


def test_emit_control_queue_depth_no_broker_connection_is_noop():
    statsd = FakeStatsdClient()
    queue_metrics.emit_control_queue_depth(
        cast(VanillaGalaxyStatsdClient, statsd), None, cast(ApplicationStack, MagicMock())
    )
    assert statsd.timings == []


# ---------------------------------------------------------------------------
# emit_queue_metrics — aggregate entry-point
# ---------------------------------------------------------------------------


def test_emit_queue_metrics_is_silent_when_statsd_is_none():
    """No statsd client → every sub-call is skipped, no DB or broker access."""
    # Would raise AttributeError if the short-circuit didn't fire before any
    # real collaborator was touched.
    queue_metrics.emit_queue_metrics(
        statsd_client=None,
        connection=None,
        application_stack=cast(ApplicationStack, MagicMock()),
        model=cast(GalaxyModelMapping, MagicMock()),
        sse_manager=None,
    )


def test_emit_queue_metrics_isolates_real_subemitter_failures(monkeypatch):
    """When real sub-emitters raise, ``_run`` contains the failure and logs an error counter.

    We drive the failures through the actual sub-emitter bodies — not monkey-
    patched side_effects — by handing in a connection whose ``.clone()`` raises
    (for ``emit_control_queue_depth``) and a model whose ``.new_session()``
    raises (for ``emit_worker_process_gauge``). The SSE gauge is given healthy
    collaborators and should still land.
    """
    statsd = FakeStatsdClient()
    sse_manager = _fake_sse_manager(broadcast=2, per_user=1)

    broken_connection = MagicMock()
    broken_connection.clone.side_effect = RuntimeError("broker is gone")

    broken_model = MagicMock()
    broken_model.new_session.side_effect = RuntimeError("db is gone")

    # Ensure the broker path reaches .clone() rather than short-circuiting on
    # an empty queue list.
    monkeypatch.setattr(
        queue_metrics,
        "all_control_queues_for_declare",
        lambda stack: [_make_fake_queue("control.main@h", 0)],
    )

    # Must not raise — the SSE gauge still lands.
    queue_metrics.emit_queue_metrics(
        statsd_client=cast(VanillaGalaxyStatsdClient, statsd),
        connection=broken_connection,
        application_stack=cast(ApplicationStack, MagicMock()),
        model=cast(GalaxyModelMapping, broken_model),
        sse_manager=sse_manager,
    )

    # SSE gauge landed despite the other two failing.
    sse_timings = statsd.timings_for("galaxy.sse.connections.active")
    assert (2, {"kind": "broadcast"}) in sse_timings
    assert (1, {"kind": "per_user"}) in sse_timings

    # Each failing sub-emitter bumped its error counter tagged by name.
    assert statsd.counter("galaxy.queue_metrics.error", {"emitter": "control_queue_depth"}) == 1
    assert statsd.counter("galaxy.queue_metrics.error", {"emitter": "worker_process"}) == 1
    # The healthy SSE sub-emitter did not.
    assert statsd.counter("galaxy.queue_metrics.error", {"emitter": "sse_connections"}) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

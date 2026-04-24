"""Producer-side SSE helper: fans events out across Galaxy processes.

Kept in its own module (separate from ``galaxy.managers.sse``) because the
dispatcher depends on ``galaxy.queue_worker`` and ``galaxy.queues``, while
``queue_worker`` in turn depends on the connection types in ``sse``. Splitting
the producer (``SSEEventDispatcher``) from the connection state
(``SSEConnectionManager`` / ``SSEEvent``) breaks that cycle without requiring
inline imports in the hot path.
"""

import logging
import threading
import time
from collections.abc import Callable
from typing import (
    Any,
    Optional,
    Protocol,
)

from cachetools import TTLCache
from kombu import Queue

from galaxy.managers.sse import make_event_id
from galaxy.queue_worker import (
    ControlTask,
    GalaxyQueueWorker,
)
from galaxy.queues import all_control_queues_for_declare
from galaxy.web.statsd_client import VanillaGalaxyStatsdClient
from galaxy.web_stack import ApplicationStack


class ControlTaskLike(Protocol):
    """Structural type for the dispatcher's control-task collaborator.

    The dispatcher only calls ``send_task(**kwargs)``. Typed as a Protocol so
    tests can pass lightweight fakes (``FakeControlTask``, ``NoopControlTask``)
    without subclassing ``ControlTask``.
    """

    def send_task(self, **kwargs: Any) -> Any: ...

log = logging.getLogger(__name__)


class SSEEventDispatcher:
    """Fans out SSE events across all Galaxy worker processes via the control queue.

    Dependencies are injected individually so the dispatcher can be unit-tested
    without a full ``app``. ``queue_worker`` is ``Optional`` because unit-test
    mock apps and Galaxy configurations without AMQP don't construct one — the
    dispatcher silently no-ops in that case.

    ``statsd_client`` is optional — if ``None`` (statsd not configured), all
    instrumentation becomes a cheap attribute-lookup no-op.
    """

    # TTL for the active-worker declare-queue cache. The WorkerProcess heartbeat
    # writes every 60 s and ``all_control_queues_for_declare`` filters on a 120 s
    # window, so a 30 s cache cannot produce a result that wasn't also valid in
    # the non-cached call. Surfaced as a class constant so tests can monkey-patch.
    _DECLARE_QUEUES_TTL_SECONDS = 30

    def __init__(
        self,
        queue_worker: Optional[GalaxyQueueWorker],
        application_stack: ApplicationStack,
        statsd_client: Optional[VanillaGalaxyStatsdClient] = None,
        clock: Callable[[], float] = time.monotonic,
        control_task_factory: Callable[[GalaxyQueueWorker], ControlTaskLike] = ControlTask,
        queues_provider: Optional[Callable[[], list[Queue]]] = None,
    ) -> None:
        self._queue_worker = queue_worker
        self._application_stack = application_stack
        self._statsd_client = statsd_client
        self._clock = clock
        self._control_task_factory = control_task_factory
        # Default provider closes over application_stack so tests can pass a
        # plain ``lambda: [...]`` without needing a stack.
        self._queues_provider = queues_provider or (
            lambda: all_control_queues_for_declare(application_stack, webapp_only=True)
        )
        self._declare_queues_cache: TTLCache = TTLCache(maxsize=1, ttl=self._DECLARE_QUEUES_TTL_SECONDS, timer=clock)
        self._declare_queues_lock = threading.RLock()

    def _get_declare_queues(self) -> list[Queue]:
        # Empty results (startup before DatabaseHeartbeat registers this process,
        # or a transient DB error swallowed by the provider) must not be pinned
        # for the full TTL — they'd silently drop every SSE event until the next
        # expiry. Only cache non-empty results.
        with self._declare_queues_lock:
            try:
                return self._declare_queues_cache["webapp"]
            except KeyError:
                queues = self._queues_provider()
                if queues:
                    self._declare_queues_cache["webapp"] = queues
                return queues

    def _send(self, task: str, kwargs: dict[str, Any]) -> None:
        if self._queue_worker is None:
            # AMQP not configured at all (e.g. unit-test mock app). Skip silently.
            log.debug("SSE dispatch skipped: no queue_worker configured (task=%s)", task)
            if self._statsd_client is not None:
                self._statsd_client.incr("galaxy.sse.dispatch.skipped_no_qw")
            return
        if self._statsd_client is not None:
            self._statsd_client.incr("galaxy.sse.dispatch.count", tags={"task": task})
        # Only fan out to webapp processes — job handlers and workflow schedulers
        # don't have browser SSE connections to push to.
        declare_queues = self._get_declare_queues()
        control_task = self._control_task_factory(self._queue_worker)
        start_time = time.perf_counter() if self._statsd_client is not None else 0.0
        try:
            control_task.send_task(
                payload={"task": task, "kwargs": kwargs},
                routing_key="control.*",
                expiration=10,
                declare_queues=declare_queues,
            )
        finally:
            if self._statsd_client is not None:
                dt_ms = int((time.perf_counter() - start_time) * 1000)
                self._statsd_client.timing("galaxy.sse.dispatch.latency_ms", dt_ms, tags={"task": task})

    def notify_users(self, user_ids: list[int], payload: str, event_id: Optional[str] = None) -> None:
        self._send(
            "notify_users",
            {
                "user_ids": user_ids,
                "payload": payload,
                "event_id": event_id or make_event_id(),
            },
        )

    def notify_broadcast(self, payload: str, event_id: Optional[str] = None) -> None:
        self._send(
            "notify_broadcast",
            {
                "payload": payload,
                "event_id": event_id or make_event_id(),
            },
        )

    def history_update(
        self,
        user_updates: dict[str, list[int]],
        event_id: Optional[str] = None,
        session_updates: Optional[dict[str, list[int]]] = None,
    ) -> None:
        kwargs: dict[str, Any] = {
            "user_updates": user_updates,
            "event_id": event_id or make_event_id(),
        }
        if session_updates:
            # Only include when non-empty: anonymous histories are uncommon on
            # most deployments, and an empty dict is wasted wire payload.
            kwargs["session_updates"] = session_updates
        self._send("history_update", kwargs)

    def entry_point_update(self, user_id: int, event_id: Optional[str] = None) -> None:
        """Fan out a wake-up ``entry_point_update`` event for one user.

        The client always refetches the canonical entry-point list on receipt,
        so no IDs are sent — keeping the payload small and the dispatch path
        free of per-event encoding work.
        """
        self._send(
            "entry_point_update",
            {
                "user_id": user_id,
                "event_id": event_id or make_event_id(),
            },
        )

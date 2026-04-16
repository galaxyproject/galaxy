"""Server-Sent Events (SSE) connection manager for real-time notifications.

Manages per-worker in-memory mapping of user IDs to asyncio.Queue instances,
enabling push of events from any thread (e.g. Kombu control queue worker)
to async SSE endpoint handlers running in the uvicorn event loop.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import (
    AsyncIterator,
    Optional,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from starlette.requests import Request

    from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    """An event to be sent to an SSE client."""

    event: str  # e.g. "notification_update", "broadcast_update", "notification_status"
    data: str  # JSON payload
    id: Optional[str] = None  # ISO timestamp, used by EventSource as Last-Event-ID on reconnect

    def to_wire(self) -> str:
        """Serialize this event to the SSE wire format (``event:…\\ndata:…\\n[id:…\\n]\\n``)."""
        frame = f"event: {self.event}\ndata: {self.data}\n"
        if self.id:
            frame += f"id: {self.id}\n"
        return frame + "\n"


class SSEConnectionManager:
    """Per-worker manager for SSE connections.

    Maps user_ids to sets of asyncio.Queue instances. Each SSE connection
    gets its own queue. The manager is thread-safe for push operations
    via ``loop.call_soon_threadsafe``.

    Lifecycle:
    - Instantiated once per Galaxy worker process (on app object).
    - ``connect()`` is called from the SSE async endpoint (event loop thread).
    - ``disconnect()`` is called from the SSE endpoint's ``finally`` block.
    - ``push_to_user()`` / ``push_broadcast()`` are called from ANY thread
      (typically the Kombu daemon thread via control task handlers).
    """

    def __init__(self) -> None:
        self._connections: dict[int, set[asyncio.Queue]] = defaultdict(set)
        self._broadcast_connections: set[asyncio.Queue] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _ensure_loop(self) -> None:
        """Capture the running asyncio event loop. Must be called from async context."""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.get_running_loop()

    # -- Called from ASYNC context (uvicorn event loop thread) --

    def connect(self, user_id: Optional[int]) -> asyncio.Queue:
        """Register a new SSE connection. Returns a queue to await events from.

        Called from the SSE endpoint handler (async context). A ``ready`` event is
        enqueued immediately so that clients (and tests) can synchronize on the
        server-side subscription rather than the underlying socket open event.
        """
        self._ensure_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=64)
        if user_id is not None:
            self._connections[user_id].add(queue)
        self._broadcast_connections.add(queue)
        queue.put_nowait(SSEEvent(event="ready", data=""))
        log.debug(
            "SSE connection opened for user_id=%s (total=%d)",
            user_id,
            len(self._broadcast_connections),
        )
        return queue

    def disconnect(self, user_id: Optional[int], queue: asyncio.Queue) -> None:
        """Unregister an SSE connection.

        Called from the SSE endpoint's ``finally`` block (async context).
        """
        if user_id is not None:
            self._connections[user_id].discard(queue)
            if not self._connections[user_id]:
                del self._connections[user_id]
        self._broadcast_connections.discard(queue)
        log.debug(
            "SSE connection closed for user_id=%s (total=%d)",
            user_id,
            len(self._broadcast_connections),
        )

    # -- Called from ANY thread (Kombu thread or async) --

    def push_to_user(self, user_id: int, event: SSEEvent) -> None:
        """Thread-safe. Push an event to all SSE connections for a specific user."""
        for queue in list(self._connections.get(user_id, [])):
            self._safe_put(queue, event)

    def push_broadcast(self, event: SSEEvent) -> None:
        """Thread-safe. Push an event to ALL connected SSE clients."""
        for queue in list(self._broadcast_connections):
            self._safe_put(queue, event)

    def _safe_put(self, queue: asyncio.Queue, event: SSEEvent) -> None:
        """Cross the thread boundary safely using ``call_soon_threadsafe``."""
        if self._loop is None or self._loop.is_closed():
            return
        try:
            self._loop.call_soon_threadsafe(self._do_put, queue, event)
        except RuntimeError:
            # Event loop is closed or shutting down
            pass

    @staticmethod
    def _do_put(queue: asyncio.Queue, event: SSEEvent) -> None:
        """Runs ON the event loop thread. Safe to touch asyncio.Queue here."""
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("SSE queue full, dropping event: %s", event.event)

    @property
    def connected_user_ids(self) -> set[int]:
        return set(self._connections.keys())

    @property
    def total_connections(self) -> int:
        return len(self._broadcast_connections)

    # -- High-level streaming helper --

    async def stream(
        self,
        request: "Request",
        user_id: Optional[int],
        catch_up: Optional[SSEEvent] = None,
        keepalive: float = 30.0,
    ) -> AsyncIterator[str]:
        """Yield SSE-framed strings for one connected client.

        Handles ``connect``, optional catch-up event priming, the main event
        loop with a keepalive comment on timeout, disconnect detection, and
        ``disconnect`` in ``finally``. Controllers should call this and return
        the iterator wrapped in a ``StreamingResponse``.
        """
        queue = self.connect(user_id)
        if catch_up is not None:
            await queue.put(catch_up)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event: SSEEvent = await asyncio.wait_for(queue.get(), timeout=keepalive)
                    yield event.to_wire()
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            self.disconnect(user_id, queue)


class SSEEventDispatcher:
    """Fans out SSE events across all Galaxy worker processes via the control queue.

    Thin wrapper around ``send_control_task`` so that managers can depend on a
    narrow, injectable collaborator instead of importing the queue-worker
    module directly. Works in both web-worker and Celery-worker contexts —
    ``GalaxyManagerApplication`` sets up a publisher-only ``queue_worker`` for
    the Celery side.
    """

    def __init__(self, app: "MinimalManagerApp") -> None:
        self._app = app

    def _send(self, task: str, kwargs: dict) -> None:
        if getattr(self._app, "queue_worker", None) is None:
            # AMQP not configured at all (e.g. unit-test mock app). Skip silently.
            log.debug("SSE dispatch skipped: no queue_worker configured (task=%s)", task)
            return
        from galaxy.queue_worker import send_control_task  # circular: queue_worker -> app -> managers
        from galaxy.queues import all_control_queues_for_declare

        # Only fan out to webapp processes — job handlers and workflow schedulers
        # don't have browser SSE connections to push to.
        declare_queues = all_control_queues_for_declare(self._app.application_stack, webapp_only=True)
        send_control_task(self._app, task, kwargs=kwargs, expiration=10, declare_queues=declare_queues)

    def notify_users(self, user_ids: list[int], payload: str, event_id: Optional[str] = None) -> None:
        self._send(
            "notify_users",
            {
                "user_ids": user_ids,
                "payload": payload,
                "event_id": event_id or datetime.utcnow().isoformat(),
            },
        )

    def notify_broadcast(self, payload: str, event_id: Optional[str] = None) -> None:
        self._send(
            "notify_broadcast",
            {
                "payload": payload,
                "event_id": event_id or datetime.utcnow().isoformat(),
            },
        )

    def history_update(self, user_updates: dict[str, list], event_id: Optional[str] = None) -> None:
        self._send(
            "history_update",
            {
                "user_updates": user_updates,
                "event_id": event_id or datetime.utcnow().isoformat(),
            },
        )

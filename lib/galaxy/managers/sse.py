"""Server-Sent Events (SSE) connection manager for real-time notifications.

Manages per-worker in-memory mapping of user IDs to asyncio.Queue instances,
enabling push of events from any thread (e.g. Kombu control queue worker)
to async SSE endpoint handlers running in the uvicorn event loop.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
)
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Optional,
)

from galaxy.model.orm.now import now
from galaxy.web.statsd_client import VanillaGalaxyStatsdClient

log = logging.getLogger(__name__)


def make_event_id() -> str:
    """Return an SSE ``id`` string for Last-Event-ID replay.

    Uses ``galaxy.model.orm.now`` so the timestamp format matches the rest of
    Galaxy's database-backed timestamps (timezone-naive UTC). Kept in one place
    so producers and the parse path cannot drift.
    """
    return now().isoformat()


def parse_event_id(event_id: str) -> Optional[datetime]:
    """Inverse of :func:`make_event_id`. Returns ``None`` if unparseable."""
    try:
        return datetime.fromisoformat(event_id)
    except (ValueError, TypeError):
        return None


#: Async callable returning True when the client has disconnected. The SSE
#: stream loop polls this each iteration so managers don't depend on starlette.
IsDisconnected = Callable[[], Awaitable[bool]]


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

    def __init__(self, statsd_client: Optional[VanillaGalaxyStatsdClient] = None) -> None:
        self._connections: dict[int, set[asyncio.Queue]] = defaultdict(set)
        self._session_connections: dict[int, set[asyncio.Queue]] = defaultdict(set)
        self._broadcast_connections: set[asyncio.Queue] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._statsd_client = statsd_client

    def _ensure_loop(self) -> None:
        """Capture the running asyncio event loop. Must be called from async context."""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.get_running_loop()

    # -- Called from ASYNC context (uvicorn event loop thread) --

    def connect(self, user_id: Optional[int], galaxy_session_id: Optional[int] = None) -> asyncio.Queue:
        """Register a new SSE connection. Returns a queue to await events from.

        Called from the SSE endpoint handler (async context). A ``ready`` event is
        enqueued immediately so that clients (and tests) can synchronize on the
        server-side subscription rather than the underlying socket open event.

        ``galaxy_session_id`` is the dispatch key for events that target a
        specific browser session (e.g. history updates for anonymous users,
        whose ``user_id`` is ``None``).
        """
        self._ensure_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=64)
        if user_id is not None:
            self._connections[user_id].add(queue)
        if galaxy_session_id is not None:
            self._session_connections[galaxy_session_id].add(queue)
        self._broadcast_connections.add(queue)
        queue.put_nowait(SSEEvent(event="ready", data=""))
        log.debug(
            "SSE connection opened for user_id=%s session_id=%s (total=%d)",
            user_id,
            galaxy_session_id,
            len(self._broadcast_connections),
        )
        return queue

    def disconnect(
        self,
        user_id: Optional[int],
        queue: asyncio.Queue,
        galaxy_session_id: Optional[int] = None,
    ) -> None:
        """Unregister an SSE connection.

        Called from the SSE endpoint's ``finally`` block (async context).
        """
        if user_id is not None:
            self._connections[user_id].discard(queue)
            if not self._connections[user_id]:
                del self._connections[user_id]
        if galaxy_session_id is not None:
            self._session_connections[galaxy_session_id].discard(queue)
            if not self._session_connections[galaxy_session_id]:
                del self._session_connections[galaxy_session_id]
        self._broadcast_connections.discard(queue)
        log.debug(
            "SSE connection closed for user_id=%s session_id=%s (total=%d)",
            user_id,
            galaxy_session_id,
            len(self._broadcast_connections),
        )

    # -- Called from ANY thread (Kombu thread or async) --

    def push_to_user(self, user_id: int, event: SSEEvent) -> None:
        """Thread-safe. Push an event to all SSE connections for a specific user."""
        for queue in list(self._connections.get(user_id, [])):
            self._safe_put(queue, event)

    def push_to_session(self, galaxy_session_id: int, event: SSEEvent) -> None:
        """Thread-safe. Push an event to all SSE connections for a specific galaxy_session.

        Used to route per-browser events (e.g. history updates for anonymous
        histories) when there is no registered ``user_id`` to key on.
        """
        for queue in list(self._session_connections.get(galaxy_session_id, [])):
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

    def _do_put(self, queue: asyncio.Queue, event: SSEEvent) -> None:
        """Runs ON the event loop thread. Safe to touch asyncio.Queue here."""
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            log.warning("SSE queue full, dropping event: %s", event.event)
            if self._statsd_client is not None:
                self._statsd_client.incr("galaxy.sse.connections.dropped")

    @property
    def connected_user_ids(self) -> set[int]:
        return set(self._connections.keys())

    @property
    def total_connections(self) -> int:
        return len(self._broadcast_connections)

    @property
    def total_broadcast_connections(self) -> int:
        """Number of all active SSE connections (includes anonymous).

        Every connection is added to ``_broadcast_connections``; this is the
        most accurate "SSE clients currently connected" gauge.
        """
        return len(self._broadcast_connections)

    @property
    def total_per_user_connections(self) -> int:
        """Number of active SSE connections bound to a specific user_id."""
        return sum(len(queues) for queues in self._connections.values())

    # -- High-level streaming helper --

    async def stream(
        self,
        is_disconnected: IsDisconnected,
        user_id: Optional[int],
        catch_up: Optional[SSEEvent] = None,
        keepalive: float = 30.0,
        galaxy_session_id: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Yield SSE-framed strings for one connected client.

        Handles ``connect``, optional catch-up event priming, the main event
        loop with a keepalive comment on timeout, disconnect detection, and
        ``disconnect`` in ``finally``. The ``is_disconnected`` callable is
        what the service passes in (typically ``request.is_disconnected`` from
        starlette) so the manager stays framework-agnostic.
        """
        queue = self.connect(user_id, galaxy_session_id)
        if catch_up is not None:
            await queue.put(catch_up)
        try:
            while True:
                if await is_disconnected():
                    break
                try:
                    event: SSEEvent = await asyncio.wait_for(queue.get(), timeout=keepalive)
                    yield event.to_wire()
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            self.disconnect(user_id, queue, galaxy_session_id)

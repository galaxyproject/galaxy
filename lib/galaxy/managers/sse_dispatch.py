"""Producer-side SSE helper: fans events out across Galaxy processes.

Kept in its own module (separate from ``galaxy.managers.sse``) because the
dispatcher depends on ``galaxy.queue_worker`` and ``galaxy.queues``, while
``queue_worker`` in turn depends on the connection types in ``sse``. Splitting
the producer (``SSEEventDispatcher``) from the connection state
(``SSEConnectionManager`` / ``SSEEvent``) breaks that cycle without requiring
inline imports in the hot path.
"""

import logging
from datetime import datetime
from typing import (
    Optional,
    TYPE_CHECKING,
)

from galaxy.queue_worker import send_control_task
from galaxy.queues import all_control_queues_for_declare

if TYPE_CHECKING:
    from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class SSEEventDispatcher:
    """Fans out SSE events across all Galaxy worker processes via the control queue.

    Thin wrapper around ``send_control_task`` so managers can depend on a narrow,
    injectable collaborator instead of reaching into the queue-worker module
    directly. Works in both web-worker and Celery-worker contexts —
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

"""Producer-side SSE helper: fans events out across Galaxy processes.

Kept in its own module (separate from ``galaxy.managers.sse``) because the
dispatcher depends on ``galaxy.queue_worker`` and ``galaxy.queues``, while
``queue_worker`` in turn depends on the connection types in ``sse``. Splitting
the producer (``SSEEventDispatcher``) from the connection state
(``SSEConnectionManager`` / ``SSEEvent``) breaks that cycle without requiring
inline imports in the hot path.
"""

import logging
from typing import (
    Any,
    Optional,
)

from galaxy.managers.sse import make_event_id
from galaxy.queue_worker import (
    ControlTask,
    GalaxyQueueWorker,
)
from galaxy.queues import all_control_queues_for_declare
from galaxy.web_stack import ApplicationStack

log = logging.getLogger(__name__)


class SSEEventDispatcher:
    """Fans out SSE events across all Galaxy worker processes via the control queue.

    Dependencies are injected individually so the dispatcher can be unit-tested
    without a full ``app``. ``queue_worker`` is ``Optional`` because unit-test
    mock apps and Galaxy configurations without AMQP don't construct one — the
    dispatcher silently no-ops in that case.
    """

    def __init__(
        self,
        queue_worker: Optional[GalaxyQueueWorker],
        application_stack: ApplicationStack,
    ) -> None:
        self._queue_worker = queue_worker
        self._application_stack = application_stack

    def _send(self, task: str, kwargs: dict[str, Any]) -> None:
        if self._queue_worker is None:
            # AMQP not configured at all (e.g. unit-test mock app). Skip silently.
            log.debug("SSE dispatch skipped: no queue_worker configured (task=%s)", task)
            return
        # Only fan out to webapp processes — job handlers and workflow schedulers
        # don't have browser SSE connections to push to.
        declare_queues = all_control_queues_for_declare(self._application_stack, webapp_only=True)
        control_task = ControlTask(self._queue_worker)
        control_task.send_task(
            payload={"task": task, "kwargs": kwargs},
            routing_key="control.*",
            expiration=10,
            declare_queues=declare_queues,
        )

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

    def history_update(self, user_updates: dict[str, list[int]], event_id: Optional[str] = None) -> None:
        self._send(
            "history_update",
            {
                "user_updates": user_updates,
                "event_id": event_id or make_event_id(),
            },
        )

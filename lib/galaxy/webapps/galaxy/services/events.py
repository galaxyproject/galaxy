"""Service layer for the unified SSE events endpoint.

Unlike :class:`NotificationService.open_stream`, this service does **not**
require the notification system to be enabled — ``/api/events/stream`` also
serves history updates and other event types independent of the notification
configuration. When notifications are disabled the catch-up event is simply
skipped; the stream still delivers other push events.
"""

from collections.abc import AsyncIterator
from typing import (
    Optional,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.sse import (
    IsDisconnected,
    SSEConnectionManager,
)
from galaxy.webapps.galaxy.services.base import ServiceBase
from galaxy.webapps.galaxy.services.notifications import NotificationService


class EventsService(ServiceBase):
    def __init__(self, sse_manager: SSEConnectionManager, notifications: NotificationService):
        self.sse_manager = sse_manager
        self.notifications = notifications

    def open_stream(
        self,
        user_context: ProvidesUserContext,
        last_event_id: Optional[str],
        is_disconnected: IsDisconnected,
    ) -> AsyncIterator[str]:
        """Open an SSE events stream.

        Anonymous users still register under their ``galaxy_session.id`` so the
        server can route per-session events (e.g. ``history_update`` for
        anonymous-owned histories) even when ``user_id`` is ``None``.
        """
        user_id = user_context.user.id if not user_context.anonymous else None
        session_id = user_context.galaxy_session.id if user_context.galaxy_session else None
        catch_up = self.notifications.build_status_catchup(user_context, last_event_id)
        return self.sse_manager.stream(is_disconnected, user_id, catch_up=catch_up, galaxy_session_id=session_id)

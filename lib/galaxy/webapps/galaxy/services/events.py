"""Service layer for the unified SSE events endpoint.

Unlike :class:`NotificationService.open_stream`, this service does **not**
require the notification system to be enabled — ``/api/events/stream`` also
serves history updates and other event types independent of the notification
configuration. When notifications are disabled the catch-up event is simply
skipped; the stream still delivers other push events.
"""

from collections.abc import AsyncIterator

from galaxy.exceptions import (
    MalformedId,
    ObjectNotFound,
)
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.histories import HistoryManager
from galaxy.managers.sse import (
    IsDisconnected,
    SSEConnectionManager,
)
from galaxy.managers.sse_dispatch import SSEEventDispatcher
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase
from galaxy.webapps.galaxy.services.notifications import NotificationService


class EventsService(ServiceBase):
    def __init__(
        self,
        sse_manager: SSEConnectionManager,
        notifications: NotificationService,
        sse_dispatcher: SSEEventDispatcher,
        history_manager: HistoryManager,
        security: IdEncodingHelper,
    ) -> None:
        super().__init__(security)
        self.history_manager = history_manager
        self.sse_manager = sse_manager
        self.notifications = notifications
        self.sse_dispatcher = sse_dispatcher

    def open_stream(
        self,
        user_context: ProvidesUserContext,
        last_event_id: str | None,
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

    def subscribe_history_viewer(self, trans: ProvidesHistoryContext, history_ids: list[str]) -> None:
        """Register the requesting user/session as a viewer for each history it can access.

        Viewers receive the ids and states of a history's invocations and jobs, so histories the
        requester cannot access (or ids that do not resolve) are skipped, like requests that have
        no route back. Broadcasts via Kombu so every webapp worker tracks the subscription
        regardless of which one fielded this request.
        """
        for history_id in history_ids:
            if self._is_accessible_history(trans, history_id):
                self._dispatch_subscription(trans, history_id, subscribe=True)

    def _is_accessible_history(self, trans: ProvidesHistoryContext, history_id: str) -> bool:
        try:
            history = self.history_manager.by_id(self.decode_id(history_id))
        except (MalformedId, ObjectNotFound):
            return False
        return self.history_manager.is_accessible(history, trans.user, current_history=trans.history)

    def unsubscribe_history_viewer(self, user_context: ProvidesUserContext, history_ids: list[str]) -> None:
        for history_id in history_ids:
            self._dispatch_subscription(user_context, history_id, subscribe=False)

    def _dispatch_subscription(self, user_context: ProvidesUserContext, history_id: str, subscribe: bool) -> None:
        user_id = user_context.user.id if not user_context.anonymous else None
        session_id = user_context.galaxy_session.id if user_context.galaxy_session else None
        if user_id is None and session_id is None:
            # No way to route events back; silently skip.
            return
        if subscribe:
            self.sse_dispatcher.subscribe_history_viewer(history_id=history_id, user_id=user_id, session_id=session_id)
        else:
            self.sse_dispatcher.unsubscribe_history_viewer(
                history_id=history_id, user_id=user_id, session_id=session_id
            )

"""
API endpoint for Server-Sent Events (SSE) stream.

Provides a unified event stream for all real-time push events (notifications,
history updates, etc.) independent of the notification system configuration.
"""

import logging
from typing import Optional

from fastapi import (
    Body,
    Header,
    Request,
    status,
)
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from galaxy.managers.context import ProvidesUserContext
from galaxy.webapps.galaxy.services.events import EventsService
from . import (
    depends,
    DependsOnTrans,
    Router,
)


class HistoryViewerSubscriptionPayload(BaseModel):
    """REST payload for ``/api/events/history-subscriptions`` endpoints."""

    history_ids: list[str]


log = logging.getLogger(__name__)

router = Router(tags=["events"])


@router.cbv
class FastAPIEvents:
    service: EventsService = depends(EventsService)

    @router.get(
        "/api/events/stream",
        summary="Server-Sent Events stream for real-time updates.",
        response_class=StreamingResponse,
    )
    async def stream_events(
        self,
        request: Request,
        trans: ProvidesUserContext = DependsOnTrans,
        last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    ) -> StreamingResponse:
        """Opens a Server-Sent Events (SSE) connection that pushes real-time
        updates for notifications, history changes, and other events.

        On reconnect, the browser sends the ``Last-Event-ID`` header automatically.
        If the notification system is enabled, any notifications created since that
        timestamp are delivered as a catch-up ``notification_status`` event.

        Anonymous users receive only broadcast events.
        """
        return StreamingResponse(
            self.service.open_stream(trans, last_event_id, request.is_disconnected),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post(
        "/api/events/history-subscriptions",
        summary="Subscribe to history_update SSE events for histories you don't own.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def subscribe_history_viewer(
        self,
        payload: HistoryViewerSubscriptionPayload = Body(...),
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> None:
        """Asks every webapp worker to start routing ``history_update`` events
        for these histories to the requesting user/session, in addition to the
        default owner-routing. Idempotent: re-subscribing to the same id is a
        no-op. Clients re-send the full set after each ``EventSource.onopen``
        so reconnects don't drop subscriptions.
        """
        self.service.subscribe_history_viewer(trans, payload.history_ids)

    @router.delete(
        "/api/events/history-subscriptions",
        summary="Cancel viewer subscriptions for these histories.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def unsubscribe_history_viewer(
        self,
        payload: HistoryViewerSubscriptionPayload = Body(...),
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> None:
        self.service.unsubscribe_history_viewer(trans, payload.history_ids)

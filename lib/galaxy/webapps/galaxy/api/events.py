"""
API endpoint for Server-Sent Events (SSE) stream.

Provides a unified event stream for all real-time push events (notifications,
history updates, etc.) independent of the notification system configuration.
"""

import logging
from typing import Optional

from fastapi import (
    Header,
    Request,
)
from starlette.responses import StreamingResponse

from galaxy.managers.context import ProvidesUserContext
from galaxy.webapps.galaxy.services.events import EventsService
from . import (
    depends,
    DependsOnTrans,
    Router,
)

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

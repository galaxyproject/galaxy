"""
API operations on Notification objects.
"""

import logging
from fastapi import (
    Body,
    Path,
    Query,
    Response,
    status,
)
from galaxy.managers.notification import NotificationManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.schema import (
    CreateNotificationPayload,
)
from . import (
    depends,
    Router,
    DependsOnTrans
)

log = logging.getLogger(__name__)

router = Router(tags=["notifications"])


@router.cbv
class FastAPINotifications:
    manager: NotificationManager = depends(NotificationManager)

    @router.get("/api/notifications", summary="Displays a collection (list) of notifications.")
    def index(self):
        return self.manager.index(limit=5)

    @router.get(
        "/api/notifications",
        summary="Displays information about a notification.",
    )
    def show(self, notification_id):
        return self.manager.show(notification_id)

    @router.post("/api/notifications", summary="Create a notificaton message")
    def create(self, trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateNotificationPayload = Body(...),):
        return self.manager.create(trans, payload)

    @router.put("/api/notifications", summary="Updates a notificaton message")
    def update(self, notification_id, updated_message):
        return self.manager.update(notification_id, updated_message)

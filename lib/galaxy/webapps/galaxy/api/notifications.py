"""
API operations on Notification objects.
"""

import logging

from fastapi import Path

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.notification import NotificationManager
from galaxy.schema.schema import (
    NotificationIdField,
    NotificationListModel,
    NotificationMessageField,
    NotificationModel,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["notifications"])

NotificationIdParam: NotificationIdField = Path(..., title="ID", description="Notification ID of the notification")
NotificationMessageParam: NotificationMessageField = Path(
    ..., title="Message", description="Message of the notification"
)


def notification_to_model(notification_id, message_text):
    return NotificationModel(id=notification_id, message_text=message_text)


@router.cbv
class FastAPINotifications:
    manager: NotificationManager = depends(NotificationManager)

    @router.get("/api/notifications", summary="Displays a collection (list) of notifications.")
    def index(self) -> NotificationListModel:
        notifications = self.manager.index(limit=5)
        return NotificationListModel(
            __root__=[notification_to_model(nt.notification_id, nt.message_text) for nt in notifications]
        )

    @router.get(
        "/api/notifications",
        summary="Displays information about a notification.",
    )
    def show(
        self,
        notification_id: NotificationIdParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> NotificationModel:
        notificaton = self.manager.show(trans, notification_id)
        return notification_to_model(notification_id, notificaton.message_text)

    @router.post("/api/notifications", summary="Create a notificaton message")
    def create(
        self,
        message_text: NotificationMessageParam,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> NotificationModel:
        notification = self.manager.create(trans, message_text)
        return notification_to_model(notification.id, message_text)

    @router.put("/api/notifications", summary="Updates a notificaton message")
    def update(self, notification_id, updated_message):
        return self.manager.update(notification_id, updated_message)

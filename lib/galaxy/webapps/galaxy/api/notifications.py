"""
API operations on Notification objects.
"""

import logging

from fastapi import Body

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.notification import NotificationManager
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    NotificationListResponseModel,
    NotificationRequestModel,
    NotificationResponseModel,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["notifications"])


@router.cbv
class FastAPINotifications:
    manager: NotificationManager = depends(NotificationManager)

    @router.get("/api/notifications", summary="Displays a collection (list) of notifications.")
    def index(self) -> NotificationListResponseModel:
        return self.manager.index(limit=5)

    @router.get(
        "/api/notifications/{notification_id}",
        summary="Displays information about a notification.",
    )
    def show(
        self,
        notification_id: DecodedDatabaseIdField,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> NotificationResponseModel:
        return self.manager.show(trans, notification_id)

    @router.post("/api/notifications", summary="Create a notification message")
    def create(
        self,
        # message_text: str = Body(..., title="Message", description="Message of the notification"),
        payload: NotificationRequestModel,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> NotificationResponseModel:
        return self.manager.create(trans, payload.message_text)

    @router.put("/api/notifications", summary="Updates a notificaton message")
    def update(self, notification_id: DecodedDatabaseIdField, updated_message) -> NotificationResponseModel:
        return self.manager.update(notification_id, updated_message)

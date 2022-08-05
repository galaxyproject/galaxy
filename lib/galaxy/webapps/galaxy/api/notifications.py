"""
API operations on Notification objects.
"""

import logging

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.notification import NotificationManager
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    NotificationCreateRequestModel,
    NotificationListResponseModel,
    NotificationResponseModel,
    NotificationUpdateRequestModel,
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
    def index(
        self,
        limit: int,
        offset: int,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> NotificationListResponseModel:
        return self.manager.index(limit=limit, offset=offset)

    @router.get(
        "/api/notifications/{notification_id}",
        summary="Displays information about a notification.",
    )
    def show(
        self,
        notification_id: DecodedDatabaseIdField,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> NotificationResponseModel:
        return self.manager.show(notification_id)

    @router.post("/api/notifications", summary="Create a notification message")
    def create(
        self,
        payload: NotificationCreateRequestModel,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> NotificationResponseModel:
        return self.manager.create(payload.message_text)

    @router.put("/api/notifications/{notification_id}", summary="Updates a notificaton message")
    def update(
        self,
        notification_id: DecodedDatabaseIdField,
        payload: NotificationUpdateRequestModel,
        trans: ProvidesAppContext = DependsOnTrans,
    ) -> NotificationResponseModel:
        return self.manager.update(notification_id, payload.message_text)

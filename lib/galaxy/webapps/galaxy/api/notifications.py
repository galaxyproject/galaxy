"""
API operations on Notification objects.
"""

import logging
from typing import Optional

from galaxy.managers.context import ProvidesUserContext
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
        limit: Optional[int] = 20,
        offset: Optional[int] = None,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> NotificationListResponseModel:
        return self.manager.index(limit=limit, offset=offset)

    @router.get(
        "/api/notifications/{notification_id}",
        summary="Displays information about a notification.",
    )
    def show(
        self,
        notification_id: DecodedDatabaseIdField,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> NotificationResponseModel:
        return self.manager.show(notification_id)

    @router.post("/api/notifications", summary="Create a notification", require_admin=True)
    def create(
        self,
        payload: NotificationCreateRequestModel,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> NotificationResponseModel:
        notification = self.manager.create(payload.content)
        self.manager.associate_user_notification(payload.user_ids, notification)
        return notification

    @router.put("/api/notifications/{notification_id}", summary="Updates a notification")
    def update(
        self,
        notification_id: DecodedDatabaseIdField,
        payload: NotificationUpdateRequestModel,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> NotificationResponseModel:
        return self.manager.update(notification_id, payload.content)

"""
API operations on Notification objects.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import (
    Body,
    Path,
    Query,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.notifications import (
    BroadcastNotificationListResponse,
    NotificationBroadcastCreateRequest,
    NotificationCreateRequest,
    NotificationCreateResponse,
    NotificationsBatchRequest,
    NotificationsBatchUpdateRequest,
    NotificationStatusSummary,
    NotificationUpdateRequest,
    NotificationUserPreferences,
    UserNotificationListResponse,
    UserNotificationResponse,
)
from galaxy.webapps.galaxy.services.notifications import NotificationService
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["notifications"])


@router.cbv
class FastAPINotifications:
    service: NotificationService = depends(NotificationService)

    @router.get(
        "/api/notifications/status",
        summary="Returns the current status summary of the user's notifications.",
    )
    def get_notifications_status(
        self, trans: ProvidesUserContext = DependsOnTrans, since: Optional[datetime] = Query()
    ) -> NotificationStatusSummary:
        return self.service.get_notifications_status(trans, since)

    @router.get(
        "/api/notifications",
        summary="Returns the list of notifications associated with the user.",
    )
    def get_user_notifications(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        limit: Optional[int] = 20,
        offset: Optional[int] = None,
    ) -> UserNotificationListResponse:
        """Anonymous users cannot receive personal notifications, only broadcasted notifications."""
        return self.service.get_user_notifications(trans, limit=limit, offset=offset)

    @router.get(
        "/api/notifications/broadcast",
        summary="Returns all currently active broadcasted notifications.",
    )
    def get_broadcasted(self) -> BroadcastNotificationListResponse:
        return self.service.get_broadcasted_notifications()

    @router.get(
        "/api/notifications/{notification_id}",
        summary="Displays information about a notification.",
    )
    def show_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        notification_id: DecodedDatabaseIdField = Path(),
    ) -> UserNotificationResponse:
        user = self.service.get_authenticated_user(trans)
        return self.service.get_user_notification_detail(user, notification_id)

    @router.put(
        "/api/notifications/{notification_id}",
        summary="Updates the state of a notification.",
    )
    def update_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        notification_id: DecodedDatabaseIdField = Path(),
        payload: NotificationUpdateRequest = Body(),
    ) -> UserNotificationResponse:
        """Only Admins can update publication and expiration dates."""
        user = self.service.get_authenticated_user(trans)
        return self.service.update_notification(user, notification_id, payload)

    @router.put(
        "/api/notifications",
        summary="Updates a list of notifications with the requested values.",
    )
    def update_notifications(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: NotificationsBatchUpdateRequest = Body(),
    ) -> UserNotificationResponse:
        """Only Admins can update publication and expiration dates."""
        user = self.service.get_authenticated_user(trans)
        return self.service.update_notifications(user, set(payload.notification_ids), payload.changes)

    @router.delete(
        "/api/notifications/{notification_id}",
        summary="Deletes a notification.",
    )
    def delete_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        notification_id: DecodedDatabaseIdField = Path(),
    ) -> UserNotificationResponse:
        user = self.service.get_authenticated_user(trans)
        delete_request = NotificationUpdateRequest(deleted=True)
        return self.service.update_notification(user, notification_id, delete_request)

    @router.delete(
        "/api/notifications",
        summary="Deletes a list of notifications.",
    )
    def delete_notifications(
        self, trans: ProvidesUserContext = DependsOnTrans, payload: NotificationsBatchRequest = Body()
    ) -> UserNotificationResponse:
        user = self.service.get_authenticated_user(trans)
        delete_request = NotificationUpdateRequest(deleted=True)
        return self.service.update_notifications(user, set(payload.notification_ids), delete_request)

    @router.post(
        "/api/notifications",
        summary="Sends a notification to a list of recipients (users, groups or roles).",
        require_admin=True,
    )
    def send_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: NotificationCreateRequest = Body(),
    ) -> NotificationCreateResponse:
        """Sends a notification to a list of recipients (users, groups or roles)."""
        return self.service.send_notification(sender_context=trans, payload=payload)

    @router.post(
        "/api/notifications/broadcast",
        summary="Broadcasts a notification to every user.",
        require_admin=True,
    )
    def broadcast_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: NotificationBroadcastCreateRequest = Body(),
    ) -> NotificationCreateResponse:
        """These special kind of notifications will be always included in every notification list request of the user."""
        return self.service.broadcast(sender_context=trans, payload=payload)

    @router.get(
        "/api/notifications/preferences",
        summary="Displays the user's preferences for notifications.",
    )
    def get_notification_preferences(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> NotificationUserPreferences:
        user = self.service.get_authenticated_user(trans)
        return self.service.get_user_notification_preferences(user)

    @router.put(
        "/api/notifications/preferences",
        summary="Updates the user's preferences for notifications.",
    )
    def update_notification_preferences(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: NotificationUserPreferences = Body(),
    ) -> NotificationUserPreferences:
        user = self.service.get_authenticated_user(trans)
        return self.service.update_user_notification_preferences(user, updated_preferences=payload)

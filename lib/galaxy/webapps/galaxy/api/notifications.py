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
    Response,
    status,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.notifications import (
    BroadcastNotificationCreateRequest,
    BroadcastNotificationListResponse,
    BroadcastNotificationResponse,
    NotificationBroadcastUpdateRequest,
    NotificationCreatedResponse,
    NotificationCreateRequest,
    NotificationsBatchRequest,
    NotificationsBatchUpdateResponse,
    NotificationStatusSummary,
    UpdateUserNotificationPreferencesRequest,
    UserNotificationListResponse,
    UserNotificationPreferences,
    UserNotificationResponse,
    UserNotificationsBatchUpdateRequest,
    UserNotificationUpdateRequest,
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
        summary="Returns the current status summary of the user's notifications since a particular date.",
    )
    def get_notifications_status(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        since: datetime = Query(),
    ) -> NotificationStatusSummary:
        return self.service.get_notifications_status(trans, since)

    @router.get(
        "/api/notifications/preferences",
        summary="Returns the current user's preferences for notifications.",
    )
    def get_notification_preferences(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> UserNotificationPreferences:
        return self.service.get_user_notification_preferences(trans)

    @router.put(
        "/api/notifications/preferences",
        summary="Updates the user's preferences for notifications.",
    )
    def update_notification_preferences(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: UpdateUserNotificationPreferencesRequest = Body(),
    ) -> UserNotificationPreferences:
        return self.service.update_user_notification_preferences(trans, payload)

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
        "/api/notifications/broadcast/{notification_id}",
        summary="Returns the information of a specific broadcasted notification.",
    )
    def get_broadcasted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        notification_id: DecodedDatabaseIdField = Path(),
    ) -> BroadcastNotificationResponse:
        """Only Admin users can access inactive notifications (scheduled or recently expired)."""
        return self.service.get_broadcasted_notification(trans, notification_id)

    @router.get(
        "/api/notifications/broadcast",
        summary="Returns all currently active broadcasted notifications.",
    )
    def get_all_broadcasted(self) -> BroadcastNotificationListResponse:
        return self.service.get_all_broadcasted_notifications()

    @router.get(
        "/api/notifications/{notification_id}",
        summary="Displays information about a notification received by the user.",
    )
    def show_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        notification_id: DecodedDatabaseIdField = Path(),
    ) -> UserNotificationResponse:
        user = self.service.get_authenticated_user(trans)
        return self.service.get_user_notification(user, notification_id)

    @router.put(
        "/api/notifications/broadcast/{notification_id}",
        summary="Updates the state of a broadcasted notification.",
        require_admin=True,
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def update_broadcasted_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        notification_id: DecodedDatabaseIdField = Path(),
        payload: NotificationBroadcastUpdateRequest = Body(),
    ):
        """Only Admins can update broadcasted notifications."""
        self.service.update_broadcasted_notification(trans, notification_id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api/notifications/{notification_id}",
        summary="Updates the state of a notification.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def update_user_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        notification_id: DecodedDatabaseIdField = Path(),
        payload: UserNotificationUpdateRequest = Body(),
    ):
        self.service.update_user_notification(trans, notification_id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api/notifications",
        summary="Updates a list of notifications with the requested values.",
    )
    def update_user_notifications(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: UserNotificationsBatchUpdateRequest = Body(),
    ) -> NotificationsBatchUpdateResponse:
        return self.service.update_user_notifications(trans, set(payload.notification_ids), payload.changes)

    @router.delete(
        "/api/notifications/{notification_id}",
        summary="Deletes a notification received by the user.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_user_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        notification_id: DecodedDatabaseIdField = Path(),
    ):
        delete_request = UserNotificationUpdateRequest(deleted=True)
        self.service.update_user_notification(trans, notification_id, delete_request)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/api/notifications",
        summary="Deletes a list of notifications received by the user.",
    )
    def delete_user_notifications(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: NotificationsBatchRequest = Body(),
    ) -> NotificationsBatchUpdateResponse:
        delete_request = UserNotificationUpdateRequest(deleted=True)
        return self.service.update_user_notifications(trans, set(payload.notification_ids), delete_request)

    @router.post(
        "/api/notifications",
        summary="Sends a notification to a list of recipients (users, groups or roles).",
        require_admin=True,
    )
    def send_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: NotificationCreateRequest = Body(),
    ) -> NotificationCreatedResponse:
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
        payload: BroadcastNotificationCreateRequest = Body(),
    ) -> NotificationCreatedResponse:
        """These special kind of notifications will be always accessible to the user."""
        return self.service.broadcast(sender_context=trans, payload=payload)

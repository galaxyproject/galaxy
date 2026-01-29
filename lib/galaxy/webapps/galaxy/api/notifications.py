"""
API operations on Notification objects.
"""

import logging
from typing import (
    Optional,
    Union,
)

from fastapi import (
    Body,
    Query,
    Response,
    status,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.notifications import (
    BroadcastNotificationCreateRequest,
    BroadcastNotificationListResponse,
    BroadcastNotificationResponse,
    NotificationBroadcastUpdateRequest,
    NotificationCreatedResponse,
    NotificationCreateRequestBody,
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
from galaxy.schema.schema import AsyncTaskResultSummary
from galaxy.schema.types import OffsetNaiveDatetime
from galaxy.webapps.galaxy.api.common import NotificationIdPathParam
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
        since: OffsetNaiveDatetime = Query(),
    ) -> NotificationStatusSummary:
        """Anonymous users cannot receive personal notifications, only broadcasted notifications."""
        return self.service.get_notifications_status(trans, since)

    @router.get(
        "/api/notifications/preferences",
        summary="Returns the current user's preferences for notifications.",
    )
    def get_notification_preferences(
        self,
        response: Response,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> UserNotificationPreferences:
        """Anonymous users cannot have notification preferences. They will receive only broadcasted notifications.

        - The settings will contain all possible channels, but the client should only show the ones that are really supported by the server.
          The supported channels are returned in the `supported-channels` header.
        """
        result = self.service.get_user_notification_preferences(trans)
        # Inform the client which channels are really supported by the server since the settings will contain all possible channels.
        response.headers["supported-channels"] = str.join(
            ",", self.service.notification_manager.get_supported_channels()
        )
        return result

    @router.put(
        "/api/notifications/preferences",
        summary="Updates the user's preferences for notifications.",
    )
    def update_notification_preferences(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: UpdateUserNotificationPreferencesRequest = Body(),
    ) -> UserNotificationPreferences:
        """Anonymous users cannot have notification preferences. They will receive only broadcasted notifications.

        - Can be used to completely enable/disable notifications for a particular type (category)
        or to enable/disable a particular channel on each category.
        """
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
        """Anonymous users cannot receive personal notifications, only broadcasted notifications.

        You can use the `limit` and `offset` parameters to paginate through the notifications.
        """
        return self.service.get_user_notifications(trans, limit=limit, offset=offset)

    @router.get(
        "/api/notifications/broadcast/{notification_id}",
        summary="Returns the information of a specific broadcasted notification.",
    )
    def get_broadcasted(
        self,
        notification_id: NotificationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> BroadcastNotificationResponse:
        """Only Admin users can access inactive notifications (scheduled or recently expired)."""
        return self.service.get_broadcasted_notification(trans, notification_id)

    @router.get(
        "/api/notifications/broadcast",
        summary="Returns all currently active broadcasted notifications.",
    )
    def get_all_broadcasted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> BroadcastNotificationListResponse:
        """Only Admin users can access inactive notifications (scheduled or recently expired)."""
        return self.service.get_all_broadcasted_notifications(trans)

    @router.get(
        "/api/notifications/{notification_id}",
        summary="Displays information about a notification received by the user.",
    )
    def show_notification(
        self,
        notification_id: NotificationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
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
        notification_id: NotificationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: NotificationBroadcastUpdateRequest = Body(),
    ):
        """Only Admins can update broadcasted notifications. This is useful to reschedule, edit or expire broadcasted notifications."""
        self.service.update_broadcasted_notification(trans, notification_id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api/notifications/{notification_id}",
        summary="Updates the state of a notification received by the user.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def update_user_notification(
        self,
        notification_id: NotificationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: UserNotificationUpdateRequest = Body(),
    ):
        self.service.update_user_notification(trans, notification_id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/api/notifications",
        summary="Updates a list of notifications with the requested values in a single request.",
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
        notification_id: NotificationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """When a notification is deleted, it is not immediately removed from the database, but marked as deleted.

        - It will not be returned in the list of notifications, but admins can still access it as long as it is not expired.
        - It will be eventually removed from the database by a background task after the expiration time.
        - Deleted notifications will be permanently deleted when the expiration time is reached.
        """
        delete_request = UserNotificationUpdateRequest(deleted=True)
        self.service.update_user_notification(trans, notification_id, delete_request)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/api/notifications",
        summary="Deletes a list of notifications received by the user in a single request.",
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
        payload: NotificationCreateRequestBody = Body(),
    ) -> Union[NotificationCreatedResponse, AsyncTaskResultSummary]:
        """Sends a notification to a list of recipients (users, groups or roles)."""
        return self.service.send_notification(sender_context=trans, payload=payload)

    @router.post(
        "/api/notifications/broadcast",
        summary="Broadcasts a notification to every user in the system.",
        require_admin=True,
    )
    def broadcast_notification(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: BroadcastNotificationCreateRequest = Body(),
    ) -> NotificationCreatedResponse:
        """Broadcasted notifications are a special kind of notification that are always accessible to all users, including anonymous users.
        They are typically used to display important information such as maintenance windows or new features.
        These notifications are displayed differently from regular notifications, usually in a banner at the top or bottom of the page.

        Broadcasted notifications can include action links that are displayed as buttons.
        This allows users to easily perform tasks such as filling out surveys, accepting legal agreements, or accessing new tutorials.

        Some key features of broadcasted notifications include:
        - They are not associated with a specific user, so they cannot be deleted or marked as read.
        - They can be scheduled to be displayed in the future or to expire after a certain time.
        - By default, broadcasted notifications are published immediately and expire six months after publication.
        - Only admins can create, edit, reschedule, or expire broadcasted notifications as needed.
        """
        return self.service.broadcast(sender_context=trans, payload=payload)

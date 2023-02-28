from datetime import datetime
from typing import (
    Optional,
    Set,
)

from galaxy.exceptions import AdminRequiredException
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.notification import NotificationManager
from galaxy.model import User
from galaxy.schema.notifications import (
    BroadcastNotificationListResponse,
    BroadcastNotificationResponse,
    NotificationBroadcastCreateRequest,
    NotificationCreateRequest,
    NotificationCreateResponse,
    NotificationResponse,
    NotificationStatusSummary,
    NotificationUpdateRequest,
    NotificationUserPreferences,
    UserNotificationListResponse,
    UserNotificationResponse,
)
from galaxy.webapps.galaxy.services.base import ServiceBase


class NotificationService(ServiceBase):
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager

    def send_notification(
        self, sender_context: ProvidesUserContext, payload: NotificationCreateRequest
    ) -> NotificationCreateResponse:
        """Sends a notification to a list of recipients (users, groups or roles)."""
        self._ensure_user_can_send_notifications(sender_context)
        notification, recipient_user_count = self.notification_manager.create_notification_for_users(payload)
        return NotificationCreateResponse(
            total_notifications_sent=recipient_user_count, notification=NotificationResponse.from_orm(notification)
        )

    def broadcast(
        self, sender_context: ProvidesUserContext, payload: NotificationBroadcastCreateRequest
    ) -> NotificationCreateResponse:
        """Creates a notification broadcast.

        Broadcasted notifications are a special type of notification are accessible by every user.
        """
        self._ensure_user_can_broadcast_notifications(sender_context)
        notification = self.notification_manager.create_broadcast_notification(payload)
        return NotificationCreateResponse(
            total_notifications_sent=1, notification=NotificationResponse.from_orm(notification)
        )

    def get_notifications_status(
        self, user_context: ProvidesUserContext, since: Optional[datetime] = None
    ) -> NotificationStatusSummary:
        """Returns the status (unread or updated) of notifications received by the user **since** a particular date and time.

        If the user is **anonymous**, only the `broadcasted notifications` will be returned.
        """
        raise NotImplementedError

    def get_user_notifications(
        self, user_context: ProvidesUserContext, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> UserNotificationListResponse:
        """Returns all the notifications received by the user that haven't expired yet..

        **Anonymous** users cannot receive personal notifications.
        """
        if user_context.anonymous:
            return UserNotificationListResponse(__root__=[])
        notifications = self.notification_manager.get_user_notifications(user_context.user, limit, offset)
        user_notifications = [UserNotificationResponse.from_orm(notification) for notification in notifications]
        return UserNotificationListResponse(__root__=user_notifications)

    def get_broadcasted_notifications(self) -> BroadcastNotificationListResponse:
        """Gets all the `broadcasted` notifications currently published."""
        notifications = self.notification_manager.get_all_broadcasted_notifications()
        broadcasted_notifications = [
            BroadcastNotificationResponse.from_orm(notification) for notification in notifications
        ]
        return BroadcastNotificationListResponse(__root__=broadcasted_notifications)

    def get_user_notification_detail(self, user: User, notification_id: int) -> UserNotificationResponse:
        """TODO"""
        raise NotImplementedError

    def update_notification(self, user: User, notification_id: int, request: NotificationUpdateRequest):
        """Updates a single notification with the requested values."""
        return self.update_notifications(user, set([notification_id]), request)

    def update_notifications(self, user: User, notification_ids: Set[int], request: NotificationUpdateRequest):
        """TODO"""
        raise NotImplementedError

    def get_user_notification_preferences(self, user: User) -> NotificationUserPreferences:
        """TODO"""
        raise NotImplementedError

    def update_user_notification_preferences(
        self, user: User, updated_preferences: NotificationUserPreferences
    ) -> NotificationUserPreferences:
        """TODO"""
        raise NotImplementedError

    def _ensure_user_can_send_notifications(self, sender_context: ProvidesUserContext) -> None:
        """Raises an exception if the user cannot send notifications."""
        # TODO implement and check permissions for non-admin users?
        if not sender_context.user_is_admin:
            raise AdminRequiredException("Only administrators can create and send notifications.")

    def _ensure_user_can_broadcast_notifications(self, sender_context: ProvidesUserContext) -> None:
        """Raises an exception if the user cannot broadcast notifications."""
        # TODO implement and check permissions for non-admin users?
        if not sender_context.user_is_admin:
            raise AdminRequiredException("Only administrators can broadcast notifications.")

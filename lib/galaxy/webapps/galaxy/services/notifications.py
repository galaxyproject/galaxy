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
    NotificationBroadcastCreateRequest,
    NotificationCreateRequest,
    NotificationCreateResponse,
    NotificationListResponse,
    NotificationResponse,
    NotificationStatusSummary,
    NotificationUpdateRequest,
    NotificationUserPreferences,
    UserNotificationResponse,
)
from galaxy.webapps.galaxy.services.base import ServiceBase


class NotificationService(ServiceBase):
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager

    def send_notification(
        self, sender: ProvidesUserContext, payload: NotificationCreateRequest
    ) -> NotificationCreateResponse:
        """Sends a notification to a list of recipients (users, groups or roles)."""
        # TODO check the sender permission to send notifications (currently only admins can)
        if not sender.user_is_admin:
            raise AdminRequiredException("Only administrators can create notifications.")
        notification, recipient_user_count = self.notification_manager.create_notification_for_users(payload)
        return NotificationCreateResponse(
            total_notifications_sent=recipient_user_count, notification=NotificationResponse.from_orm(notification)
        )

    def broadcast(
        self, sender: ProvidesUserContext, payload: NotificationBroadcastCreateRequest
    ) -> NotificationCreateResponse:
        """TODO"""
        raise NotImplementedError

    def get_notifications_status(
        self, user: Optional[User], since: Optional[datetime] = None
    ) -> NotificationStatusSummary:
        """Returns the status (unread or updated notifications) of the user's notifications since a particular date and time.

        If the user is **anonymous**, only the `broadcasted notifications` will be returned.
        """
        if user is None:
            return self.get_broadcasted_notifications_status(since)
        return self.get_user_notifications_status(user, since)

    def get_broadcasted_notifications_status(self, since: Optional[datetime] = None) -> NotificationStatusSummary:
        """TODO"""
        raise NotImplementedError

    def get_user_notifications_status(self, user: User, since: Optional[datetime] = None) -> NotificationStatusSummary:
        """TODO"""
        raise NotImplementedError

    def get_notifications(
        self, user: Optional[User], limit: Optional[int] = None, offset: Optional[int] = None
    ) -> NotificationListResponse:
        """Returns all the notifications (paginated and/or filtered) of the user.

        If the user is **anonymous**, only the `broadcasted notifications` will be returned.
        """
        if user is None:
            return self.get_broadcasted_notifications()
        return self.get_user_notifications(user, limit, offset)

    def get_user_notifications(
        self, user: User, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> NotificationListResponse:
        """TODO"""
        notifications = self.notification_manager.get_user_notifications(user, limit, offset)
        user_notifications = [UserNotificationResponse.from_orm(notification) for notification in notifications]
        return NotificationListResponse(__root__=user_notifications)

    def get_broadcasted_notifications(self) -> NotificationListResponse:
        """TODO"""
        raise NotImplementedError

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

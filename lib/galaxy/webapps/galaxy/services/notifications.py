from datetime import datetime
from typing import (
    List,
    NoReturn,
    Optional,
    Set,
)

from galaxy.exceptions import (
    AdminRequiredException,
    AuthenticationRequired,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.notification import NotificationManager
from galaxy.model import User
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.notifications import (
    BroadcastNotificationCreateRequest,
    BroadcastNotificationListResponse,
    BroadcastNotificationResponse,
    NotificationBroadcastUpdateRequest,
    NotificationCreatedResponse,
    NotificationCreateRequest,
    NotificationResponse,
    NotificationsBatchUpdateResponse,
    NotificationStatusSummary,
    NotificationUpdateRequest,
    UpdateUserNotificationPreferencesRequest,
    UserNotificationListResponse,
    UserNotificationPreferences,
    UserNotificationResponse,
    UserNotificationUpdateRequest,
)
from galaxy.webapps.galaxy.services.base import ServiceBase


class NotificationService(ServiceBase):
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager

    def send_notification(
        self, sender_context: ProvidesUserContext, payload: NotificationCreateRequest
    ) -> NotificationCreatedResponse:
        """Sends a notification to a list of recipients (users, groups or roles)."""
        self.notification_manager.ensure_notifications_enabled()
        self._ensure_user_can_send_notifications(sender_context)
        notification, recipient_user_count = self.notification_manager.send_notification_to_recipients(payload)
        return NotificationCreatedResponse(
            total_notifications_sent=recipient_user_count, notification=NotificationResponse.from_orm(notification)
        )

    def broadcast(
        self, sender_context: ProvidesUserContext, payload: BroadcastNotificationCreateRequest
    ) -> NotificationCreatedResponse:
        """Creates a notification broadcast.

        Broadcasted notifications are a special type of notification are accessible by every user.
        """
        self.notification_manager.ensure_notifications_enabled()
        self._ensure_user_can_broadcast_notifications(sender_context)
        notification = self.notification_manager.create_broadcast_notification(payload)
        return NotificationCreatedResponse(
            total_notifications_sent=1, notification=NotificationResponse.from_orm(notification)
        )

    def get_notifications_status(self, user_context: ProvidesUserContext, since: datetime) -> NotificationStatusSummary:
        """Returns the status of (unread or updated) notifications received by the user **since** a particular date and time.

        If the user is **anonymous**, only the `broadcasted notifications` will be returned.
        """
        self.notification_manager.ensure_notifications_enabled()
        total_unread_count = 0
        broadcasts = self._get_all_broadcasted(since)
        user_notifications = []
        if not user_context.anonymous:
            total_unread_count = self.notification_manager.get_user_total_unread_notification_count(user_context.user)
            user_notifications = self._get_user_notifications(user_context, since=since)
        return NotificationStatusSummary(
            total_unread_count=total_unread_count,
            broadcasts=broadcasts,
            notifications=user_notifications,
        )

    def get_user_notifications(
        self, user_context: ProvidesUserContext, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> UserNotificationListResponse:
        """Returns all the notifications received by the user that haven't expired yet..

        **Anonymous** users cannot receive personal notifications.
        """
        self.notification_manager.ensure_notifications_enabled()
        if user_context.anonymous:
            return UserNotificationListResponse(__root__=[])
        user_notifications = self._get_user_notifications(user_context, limit, offset)
        return UserNotificationListResponse(__root__=user_notifications)

    def get_broadcasted_notification(
        self, user_context: ProvidesUserContext, notification_id: int
    ) -> BroadcastNotificationResponse:
        """Gets a single `broadcasted` notification by ID.
        Admin users can access inactive notifications (scheduled or recently expired).
        """
        self.notification_manager.ensure_notifications_enabled()
        active_only = not user_context.user_is_admin
        try:
            broadcasted_notification = self.notification_manager.get_broadcasted_notification(
                notification_id, active_only
            )
            return BroadcastNotificationResponse.from_orm(broadcasted_notification)
        except ObjectNotFound:
            self._raise_notification_not_found(notification_id)

    def get_all_broadcasted_notifications(self, user_context: ProvidesUserContext) -> BroadcastNotificationListResponse:
        """Gets all the `broadcasted` notifications currently published.
        Admin users will also get inactive notifications (scheduled or recently expired)."""
        self.notification_manager.ensure_notifications_enabled()
        active_only = not user_context.user_is_admin
        broadcasted_notifications = self._get_all_broadcasted(active_only=active_only)
        return BroadcastNotificationListResponse(__root__=broadcasted_notifications)

    def get_user_notification(self, user: User, notification_id: int) -> UserNotificationResponse:
        """Gets the information of the notification received by the user with the given ID."""
        self.notification_manager.ensure_notifications_enabled()
        try:
            notification = self.notification_manager.get_user_notification(user, notification_id)
            return UserNotificationResponse.from_orm(notification)
        except ObjectNotFound:
            self._raise_notification_not_found(notification_id)

    def update_user_notification(
        self, user_context: ProvidesUserContext, notification_id: int, request: UserNotificationUpdateRequest
    ):
        """Updates a single notification received by the user with the requested values."""
        self.notification_manager.ensure_notifications_enabled()
        updated_response = self.update_user_notifications(user_context, set([notification_id]), request)
        if not updated_response.updated_count:
            self._raise_notification_not_found(notification_id)

    def update_broadcasted_notification(
        self, user_context: ProvidesUserContext, notification_id: int, request: NotificationBroadcastUpdateRequest
    ):
        """Updates a single notification received by the user with the requested values."""
        self.notification_manager.ensure_notifications_enabled()
        self._ensure_user_can_update_broadcasted_notifications(user_context)
        self._ensure_there_are_changes(request)
        updated_count = self.notification_manager.update_broadcasted_notification(notification_id, request)
        if not updated_count:
            self._raise_notification_not_found(notification_id)

    def update_user_notifications(
        self, user_context: ProvidesUserContext, notification_ids: Set[int], request: UserNotificationUpdateRequest
    ) -> NotificationsBatchUpdateResponse:
        """Updates a batch of notifications received by the user with the requested values."""
        self.notification_manager.ensure_notifications_enabled()
        self._ensure_user_can_update_notifications(user_context)
        self._ensure_there_are_changes(request)
        updated_count = self.notification_manager.update_user_notifications(
            user_context.user, notification_ids, request
        )
        return NotificationsBatchUpdateResponse(updated_count=updated_count)

    def get_user_notification_preferences(self, user_context: ProvidesUserContext) -> UserNotificationPreferences:
        """Gets the user's current notification preferences."""
        self.notification_manager.ensure_notifications_enabled()
        user = self.get_authenticated_user(user_context)
        return self.notification_manager.get_user_notification_preferences(user)

    def update_user_notification_preferences(
        self, user_context: ProvidesUserContext, request: UpdateUserNotificationPreferencesRequest
    ) -> UserNotificationPreferences:
        """Updates the user's notification preferences with the requested changes."""
        self.notification_manager.ensure_notifications_enabled()
        user = self.get_authenticated_user(user_context)
        return self.notification_manager.update_user_notification_preferences(user, request)

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

    def _ensure_user_can_update_notifications(self, user_context: ProvidesUserContext):
        """Raises an exception if the user cannot update notifications."""
        if user_context.anonymous:
            raise AuthenticationRequired("You must be logged in to update notifications.")

    def _ensure_user_can_update_broadcasted_notifications(self, user_context: ProvidesUserContext):
        """Raises an exception if the user tries to update broadcasted notifications without permission."""
        if not user_context.user_is_admin:
            raise AdminRequiredException(
                "Only administrators can update publication and expiration times of notifications."
            )

    def _ensure_there_are_changes(self, request: NotificationUpdateRequest):
        """Raises an exception if all values are None"""
        if not request.has_changes():
            raise RequestParameterInvalidException("Please specify at least one value to update for notifications.")

    def _get_all_broadcasted(
        self, since: Optional[datetime] = None, active_only: Optional[bool] = True
    ) -> List[BroadcastNotificationResponse]:
        notifications = self.notification_manager.get_all_broadcasted_notifications(since, active_only)
        broadcasted_notifications = [
            BroadcastNotificationResponse.from_orm(notification) for notification in notifications
        ]
        return broadcasted_notifications

    def _get_user_notifications(
        self,
        user_context: ProvidesUserContext,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> List[UserNotificationResponse]:
        notifications = self.notification_manager.get_user_notifications(user_context.user, limit, offset, since)
        user_notifications = [UserNotificationResponse.from_orm(notification) for notification in notifications]
        return user_notifications

    def _raise_notification_not_found(self, notification_id: int) -> NoReturn:
        raise ObjectNotFound(
            f"The requested notification with id '{DecodedDatabaseIdField.encode(notification_id)}' was not found."
        )

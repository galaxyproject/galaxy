from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    NoReturn,
    Optional,
    Union,
)

from galaxy.celery.tasks import send_notification_to_recipients_async
from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import (
    AdminRequiredException,
    AuthenticationRequired,
    ObjectNotFound,
    RequestParameterInvalidException,
    ServerNotConfiguredForRequest,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.notification import NotificationManager
from galaxy.managers.users import UserManager
from galaxy.model import User
from galaxy.schema.fields import Security
from galaxy.schema.notifications import (
    BroadcastNotificationCreateRequest,
    BroadcastNotificationListResponse,
    BroadcastNotificationResponse,
    NotificationBroadcastUpdateRequest,
    NotificationCreateData,
    NotificationCreatedResponse,
    NotificationCreateRequest,
    NotificationCreateRequestBody,
    NotificationRecipients,
    NotificationResponse,
    NotificationsBatchUpdateResponse,
    NotificationStatusSummary,
    NotificationUpdateRequest,
    NotificationVariant,
    PersonalNotificationCategory,
    ToolRequestNotificationContent,
    UpdateUserNotificationPreferencesRequest,
    UserNotificationListResponse,
    UserNotificationPreferences,
    UserNotificationResponse,
    UserNotificationUpdateRequest,
)
from galaxy.schema.schema import AsyncTaskResultSummary
from galaxy.webapps.galaxy.services.base import (
    async_task_summary,
    ServiceBase,
)

_USER_ALLOWED_CATEGORIES: frozenset[PersonalNotificationCategory] = frozenset(
    {PersonalNotificationCategory.tool_request}
)


class NotificationService(ServiceBase):
    def __init__(
        self,
        notification_manager: NotificationManager,
        user_manager: Optional[UserManager] = None,
        config: Optional[GalaxyAppConfiguration] = None,
    ):
        self.notification_manager = notification_manager
        self.user_manager = user_manager
        self.config = config

    def send_notification(
        self, sender_context: ProvidesUserContext, payload: NotificationCreateRequestBody
    ) -> Union[NotificationCreatedResponse, AsyncTaskResultSummary]:
        """Sends a notification to a list of recipients (users, groups or roles).

        Admin users may send to arbitrary recipients with any category.
        Authenticated non-admin users may only use categories in the server-side allow-list,
        subject to per-category feature-flag checks; their recipients are overridden server-side.
        """
        self.notification_manager.ensure_notifications_enabled()
        galaxy_url = (
            str(sender_context.url_builder("/", qualified=True)).rstrip("/") if sender_context.url_builder else None
        )
        if sender_context.user_is_admin:
            request = NotificationCreateRequest.model_construct(
                notification=payload.notification,
                recipients=payload.recipients,
                galaxy_url=galaxy_url,
            )
            return self.send_notification_internal(request)

        request = self._build_user_sender_request(sender_context, payload, galaxy_url)
        # User-submitted notifications must return the created notification id synchronously,
        # so the client can link the requester directly to the new record.
        return self.send_notification_internal(request, force_sync=True)

    def _build_user_sender_request(
        self,
        sender_context: ProvidesUserContext,
        payload: NotificationCreateRequestBody,
        galaxy_url: Optional[str],
    ) -> NotificationCreateRequest:
        """Validate and rewrite a non-admin notification submission."""
        user_manager = self.user_manager
        config = self.config
        if user_manager is None or config is None:
            raise RuntimeError(
                "NotificationService requires user_manager and config for non-admin notification submissions."
            )

        if sender_context.anonymous or sender_context.user is None:
            raise AuthenticationRequired("You must be logged in to submit a notification.")

        category = payload.notification.category
        if category not in _USER_ALLOWED_CATEGORIES:
            raise AdminRequiredException("Only administrators can send notifications of this category.")

        if category == PersonalNotificationCategory.tool_request:
            if not config.enable_tool_request_form:
                raise AdminRequiredException("Tool request notifications are disabled on this Galaxy instance.")

        admin_users = user_manager.admins()
        if not admin_users:
            raise ServerNotConfiguredForRequest("No admin users are configured on this Galaxy instance.")

        sender_id = sender_context.user.id
        recipient_ids = list({u.id for u in admin_users} | {sender_id})

        content = payload.notification.content
        if category == PersonalNotificationCategory.tool_request and isinstance(
            content, ToolRequestNotificationContent
        ):
            content = content.model_copy(update={"requester_email": sender_context.user.email})

        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        notification_data = NotificationCreateData.model_construct(
            source=payload.notification.source or "tool_request_form",
            category=payload.notification.category,
            variant=payload.notification.variant or NotificationVariant.info,
            content=content,
            expiration_time=payload.notification.expiration_time or (now + timedelta(days=180)),
        )

        return NotificationCreateRequest.model_construct(
            notification=notification_data,
            recipients=NotificationRecipients(user_ids=recipient_ids),
            galaxy_url=galaxy_url,
        )

    def send_notification_internal(
        self, request: NotificationCreateRequest, force_sync: bool = False
    ) -> Union[NotificationCreatedResponse, AsyncTaskResultSummary]:
        """Sends a notification to a list of recipients (users, groups or roles).

        If `force_sync` is set to `True`, the notification recipients will be processed synchronously instead of
        in a background task.

        Note: This function is meant for internal use from other services that don't need to check sender permissions.
        """
        if self.notification_manager.can_send_notifications_async and not force_sync:
            result = send_notification_to_recipients_async.delay(request)
            summary = async_task_summary(result)
            return summary

        notification, recipient_user_count = self.notification_manager.send_notification_to_recipients(request)
        return NotificationCreatedResponse(
            total_notifications_sent=recipient_user_count,
            notification=NotificationResponse.model_validate(notification),
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
            total_notifications_sent=1, notification=NotificationResponse.model_validate(notification)
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
            return UserNotificationListResponse(root=[])
        user_notifications = self._get_user_notifications(user_context, limit, offset)
        return UserNotificationListResponse(root=user_notifications)

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
            return BroadcastNotificationResponse.model_validate(broadcasted_notification)
        except ObjectNotFound:
            self._raise_notification_not_found(notification_id)

    def get_all_broadcasted_notifications(self, user_context: ProvidesUserContext) -> BroadcastNotificationListResponse:
        """Gets all the `broadcasted` notifications currently published.
        Admin users will also get inactive notifications (scheduled or recently expired)."""
        self.notification_manager.ensure_notifications_enabled()
        active_only = not user_context.user_is_admin
        broadcasted_notifications = self._get_all_broadcasted(active_only=active_only)
        return BroadcastNotificationListResponse(root=broadcasted_notifications)

    def get_user_notification(self, user: User, notification_id: int) -> UserNotificationResponse:
        """Gets the information of the notification received by the user with the given ID."""
        self.notification_manager.ensure_notifications_enabled()
        try:
            notification = self.notification_manager.get_user_notification(user, notification_id)
            return UserNotificationResponse.model_validate(notification)
        except ObjectNotFound:
            self._raise_notification_not_found(notification_id)

    def update_user_notification(
        self, user_context: ProvidesUserContext, notification_id: int, request: UserNotificationUpdateRequest
    ):
        """Updates a single notification received by the user with the requested values."""
        self.notification_manager.ensure_notifications_enabled()
        updated_response = self.update_user_notifications(user_context, {notification_id}, request)
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
        self, user_context: ProvidesUserContext, notification_ids: set[int], request: UserNotificationUpdateRequest
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
    ) -> list[BroadcastNotificationResponse]:
        notifications = self.notification_manager.get_all_broadcasted_notifications(since, active_only)
        broadcasted_notifications = [
            BroadcastNotificationResponse.model_validate(notification) for notification in notifications
        ]
        return broadcasted_notifications

    def _get_user_notifications(
        self,
        user_context: ProvidesUserContext,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> list[UserNotificationResponse]:
        notifications = self.notification_manager.get_user_notifications(user_context.user, limit, offset, since)
        user_notifications = [UserNotificationResponse.model_validate(notification) for notification in notifications]
        return user_notifications

    def _raise_notification_not_found(self, notification_id: int) -> NoReturn:
        raise ObjectNotFound(
            f"The requested notification with id '{Security.security.encode_id(notification_id)}' was not found."
        )

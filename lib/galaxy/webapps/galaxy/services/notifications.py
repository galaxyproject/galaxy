from datetime import datetime
from typing import (
    NoReturn,
    Protocol,
)

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
from galaxy.managers.sse import (
    make_event_id,
    parse_event_id,
    SSEConnectionManager,
    SSEEvent,
)
from galaxy.managers.users import UserManager
from galaxy.model import User
from galaxy.schema.fields import Security
from galaxy.schema.notifications import (
    AnyNotificationContent,
    AnyNotificationCreateContent,
    BroadcastNotificationCreateRequest,
    BroadcastNotificationListResponse,
    BroadcastNotificationResponse,
    NotificationBroadcastUpdateRequest,
    NotificationCategory,
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
    ToolInstallationRequestCreateContent,
    ToolInstallationRequestNotificationContent,
    UpdateUserNotificationPreferencesRequest,
    UserNotificationListResponse,
    UserNotificationPreferences,
    UserNotificationResponse,
    UserNotificationUpdateRequest,
)
from galaxy.schema.schema import AsyncTaskResultSummary
from galaxy.webapps.galaxy.services.base import ServiceBase


class NotificationRequestHandler(Protocol):
    """Per-category handler for user-submitted request notifications.

    Each user-allowed request category registers a handler in
    ``_REQUEST_HANDLERS`` that owns the category-specific behavior: whether the
    feature is enabled, how the content is rewritten server-side, who the
    request is delivered to, and whether a confirmation copy is produced for the
    submitter. Adding a new request type is a new enum member + a handler
    implementing this protocol + a typed content model; the allow-list is
    derived from the registry and the service method
    (``_build_user_sender_requests``) needs no category-specific edits.
    """

    category: PersonalNotificationCategory

    def is_enabled(self, config: GalaxyAppConfiguration) -> bool:
        """Whether this request category is enabled on the instance."""
        ...

    def stamp_content(self, content: AnyNotificationCreateContent, sender: User) -> AnyNotificationContent:
        """Rewrite the client-supplied content server-side (e.g. stamp the requester email)."""
        ...

    def resolve_recipients(
        self, sender: User, config: GalaxyAppConfiguration, user_manager: UserManager
    ) -> NotificationRecipients:
        """Resolve who the request is delivered to (typically the instance admins)."""
        ...

    def build_confirmation(
        self, sender: User, admin_request: NotificationCreateRequest
    ) -> NotificationCreateRequest | None:
        """Optionally derive the submitter's confirmation copy, or None for no copy."""
        ...


class ToolInstallationRequestHandler:
    """Handler for ``tool_installation_request`` user submissions.

    Delivers the request to all instance admins and, when the submitter is not an
    admin, produces a confirmation copy for the submitter.
    """

    category = PersonalNotificationCategory.tool_installation_request

    def is_enabled(self, config: GalaxyAppConfiguration) -> bool:
        return config.enable_tool_installation_request_form

    def stamp_content(self, content: AnyNotificationCreateContent, sender: User) -> AnyNotificationContent:
        if not isinstance(content, ToolInstallationRequestCreateContent):
            return content
        # Promote the request (create) content to the persisted content model and
        # stamp the requester's real email server-side (never trust the client).
        # is_confirmation is forced False on the admin-facing copy; the service
        # decides which copy is the confirmation in build_confirmation below.
        # model_construct reuses the already-validated field values instead of
        # re-running every sanitizer and bound check on them.
        return ToolInstallationRequestNotificationContent.model_construct(
            **dict(content),
            requester_email=sender.email,
            is_confirmation=False,
        )

    def resolve_recipients(
        self, sender: User, config: GalaxyAppConfiguration, user_manager: UserManager
    ) -> NotificationRecipients:
        admin_users = user_manager.admins()
        if not admin_users:
            raise ServerNotConfiguredForRequest("No admin users are configured on this Galaxy instance.")
        return NotificationRecipients(user_ids=[u.id for u in admin_users])

    def build_confirmation(
        self, sender: User, admin_request: NotificationCreateRequest
    ) -> NotificationCreateRequest | None:
        admin_user_ids = set(admin_request.recipients.user_ids)
        if sender.id in admin_user_ids:
            # An admin submitter already receives the admin-facing request -- no separate copy.
            return None
        notification_data = admin_request.notification
        content = notification_data.content
        if not isinstance(content, ToolInstallationRequestNotificationContent):
            return None
        confirmation_content = content.model_copy(update={"is_confirmation": True})
        confirmation_notification = notification_data.model_copy(update={"content": confirmation_content})
        return admin_request.model_copy(
            update={
                "notification": confirmation_notification,
                "recipients": NotificationRecipients(user_ids=[sender.id]),
            }
        )


# Registry of per-category request handlers. To add a new user-submittable
# request type, register a handler instance here; the user allow-list is
# derived from the registry keys, so they cannot drift apart.
# _build_user_sender_requests dispatches through this registry, so it needs no
# category-specific branching for new types.
_REQUEST_HANDLERS: dict[NotificationCategory, NotificationRequestHandler] = {
    handler.category: handler for handler in (ToolInstallationRequestHandler(),)
}

_USER_ALLOWED_CATEGORIES: frozenset[NotificationCategory] = frozenset(_REQUEST_HANDLERS)


class NotificationService(ServiceBase):
    def __init__(
        self,
        notification_manager: NotificationManager,
        sse_manager: SSEConnectionManager,
        user_manager: UserManager,
        config: GalaxyAppConfiguration,
    ):
        self.notification_manager = notification_manager
        self.sse_manager = sse_manager
        self.user_manager = user_manager
        self.config = config

    @property
    def notifications_enabled(self) -> bool:
        return self.notification_manager.notifications_enabled

    def send_internal_notification(
        self, request: NotificationCreateRequest, force_sync: bool = False
    ) -> NotificationCreatedResponse | AsyncTaskResultSummary:
        """Send a system-emitted notification on behalf of internal callers (e.g. share flows).

        Unlike :meth:`send_notification`, this skips admin/permission checks because the
        caller has already resolved the recipient set and is not acting on user input.
        """
        return self.notification_manager.send_notification_internal(request, force_sync=force_sync)

    def send_notification(
        self, sender_context: ProvidesUserContext, payload: NotificationCreateRequestBody
    ) -> NotificationCreatedResponse | AsyncTaskResultSummary:
        """Sends a notification to a list of recipients (users, groups or roles).

        Admin users may send to arbitrary recipients for categories outside the user-allowed set.
        For user-allowed categories (e.g. tool installation requests), admin submissions are treated
        like regular user submissions so that recipients and content are populated server-side.

        Authenticated non-admin users may only use categories in the server-side allow-list,
        subject to per-category feature-flag checks; their recipients are overridden server-side.
        """
        self.notification_manager.ensure_notifications_enabled()
        galaxy_url = (
            str(sender_context.url_builder("/", qualified=True)).rstrip("/") if sender_context.url_builder else None
        )
        requests = self._build_user_sender_requests(sender_context, payload, galaxy_url)
        # Send each built request. The first (primary) is the admin-facing
        # notification, so the API response describes the request the admin will
        # act on -- return that one, not the last iteration's (confirmation) result.
        response: NotificationCreatedResponse | AsyncTaskResultSummary | None = None
        for index, request in enumerate(requests):
            sent = self.send_internal_notification(request, force_sync=False)
            if index == 0:
                response = sent
        assert response is not None
        return response

    def _build_user_sender_requests(
        self,
        sender_context: ProvidesUserContext,
        payload: NotificationCreateRequestBody,
        galaxy_url: str | None,
    ) -> list[NotificationCreateRequest]:
        """Validate and rewrite a user notification submission.

        For admin users sending non-user-allowed categories, passes through the payload as-is.
        For user-allowed request categories (non-admins, or admins sending such a category),
        validates the category and dispatches to the per-category ``NotificationRequestHandler``
        which rewrites recipients/content server-side and may produce a confirmation copy.

        Each handler owns its category's behavior (feature gate, content stamping, recipient
        resolution, confirmation copy). See ``_REQUEST_HANDLERS``.
        """
        category = payload.notification.category

        # Admin sending arbitrary category notification: pass through unchanged.
        if sender_context.user_is_admin and category not in _USER_ALLOWED_CATEGORIES:
            return [
                NotificationCreateRequest.model_construct(
                    notification=payload.notification,
                    recipients=payload.recipients,
                    galaxy_url=galaxy_url,
                )
            ]

        # All other cases: validate and dispatch to the request handler
        user_manager = self.user_manager
        config = self.config

        if sender_context.anonymous or sender_context.user is None:
            raise AuthenticationRequired("You must be logged in to submit a notification.")

        if category not in _USER_ALLOWED_CATEGORIES:
            raise AdminRequiredException("Only administrators can send notifications of this category.")

        handler = _REQUEST_HANDLERS[category]
        if not handler.is_enabled(config):
            # Note: pydantic validates the category union/Literal fields to plain
            # strings, so interpolating `category` yields the bare value.
            raise AdminRequiredException(f"{category} notifications are disabled on this Galaxy instance.")

        sender = sender_context.user
        assert sender is not None  # checked above

        content = handler.stamp_content(payload.notification.content, sender)

        notification_data = NotificationCreateData.model_construct(
            source=payload.notification.source or f"{category}_form",
            category=payload.notification.category,
            variant=payload.notification.variant or NotificationVariant.info,
            content=content,
            expiration_time=payload.notification.expiration_time,
        )

        # Admin-facing request: delivered to the handler-resolved recipients (the
        # submitter receives it too if they are among them, e.g. an admin).
        admin_request = NotificationCreateRequest.model_construct(
            notification=notification_data,
            recipients=handler.resolve_recipients(sender, config, user_manager),
            galaxy_url=galaxy_url,
        )
        requests = [admin_request]

        # Optional submitter confirmation copy. The handler returns None when no
        # copy is appropriate (e.g. the submitter already receives the request).
        confirmation = handler.build_confirmation(sender, admin_request)
        if confirmation is not None:
            requests.append(confirmation)

        return requests

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

    def build_status_catchup(self, user_context: ProvidesUserContext, last_event_id: str | None) -> SSEEvent | None:
        """Build a ``notification_status`` SSE event covering everything since ``last_event_id``.

        Returns ``None`` when catch-up isn't possible (no ``Last-Event-ID``,
        unparseable timestamp, or notifications disabled) so callers can simply
        pass the result to ``SSEConnectionManager.stream`` without extra guards.
        """
        if not last_event_id or not self.notification_manager.notifications_enabled:
            return None
        since = parse_event_id(last_event_id)
        if since is None:
            return None
        catchup = self.get_notifications_status(user_context, since)
        return SSEEvent(
            event="notification_status",
            data=catchup.model_dump_json(),
            id=make_event_id(),
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
        self, user_context: ProvidesUserContext, limit: int | None = None, offset: int | None = None
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
        self, since: datetime | None = None, active_only: bool | None = True
    ) -> list[BroadcastNotificationResponse]:
        notifications = self.notification_manager.get_all_broadcasted_notifications(since, active_only)
        broadcasted_notifications = [
            BroadcastNotificationResponse.model_validate(notification) for notification in notifications
        ]
        return broadcasted_notifications

    def _get_user_notifications(
        self,
        user_context: ProvidesUserContext,
        limit: int | None = None,
        offset: int | None = None,
        since: datetime | None = None,
    ) -> list[UserNotificationResponse]:
        notifications = self.notification_manager.get_user_notifications(user_context.user, limit, offset, since)
        user_notifications = [UserNotificationResponse.model_validate(notification) for notification in notifications]
        return user_notifications

    def _raise_notification_not_found(self, notification_id: int) -> NoReturn:
        raise ObjectNotFound(
            f"The requested notification with id '{Security.security.encode_id(notification_id)}' was not found."
        )

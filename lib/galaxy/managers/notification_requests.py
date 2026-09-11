"""User-submitted notification requests, e.g. tool installation requests.

A request notification is one a regular (non-admin) user may submit through
``POST /api/notifications``. The client controls only the fields on the
category's create model: a per-category :class:`NotificationRequestHandler`
gates the feature, rewrites the content server-side, resolves the recipients,
and may add a confirmation copy for the submitter.
:class:`NotificationRequestManager` owns the handler registry and turns one
submission into the notification create requests to send.
"""

from dataclasses import dataclass
from typing import Protocol

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import (
    AdminRequiredException,
    AuthenticationRequired,
    ConfigDoesNotAllowException,
    ItemAccessibilityException,
    MalformedId,
    ObjectNotFound,
    RequestParameterInvalidException,
    ServerNotConfiguredForRequest,
)
from galaxy.managers.users import UserManager
from galaxy.managers.workflows import WorkflowsManager
from galaxy.model import User
from galaxy.schema.notifications import (
    AnyInternalNotificationContent,
    AnyNotificationCreateContent,
    InternalNotificationCreateData,
    NotificationCategory,
    NotificationCreateRequest,
    NotificationCreateRequestBody,
    NotificationRecipients,
    NotificationVariant,
    PersonalNotificationCategory,
    StoredToolInstallationRequestContent,
    ToolInstallationRequestCreateContent,
)
from galaxy.work.context import SessionRequestContext


@dataclass(frozen=True)
class RequestHandlerContext:
    """What a request handler needs to know about a user submission.

    ``sender`` is the authenticated submitter (``trans.user``, already checked to
    be non-anonymous). ``host`` is the host the request was made through, for
    per-host config lookups. ``trans`` is kept for permission-checked lookups of
    referenced objects.
    """

    trans: SessionRequestContext
    sender: User
    host: str | None
    config: GalaxyAppConfiguration
    user_manager: UserManager
    workflows_manager: WorkflowsManager


class NotificationRequestHandler(Protocol):
    """Per-category handler for user-submitted request notifications.

    Each user-allowed request category registers a handler with
    :class:`NotificationRequestManager` that owns the category-specific
    behavior: whether the feature is enabled, how the content is rewritten
    server-side, who the request is delivered to, and whether a confirmation
    copy is produced for the submitter. Adding a new request type is a new enum
    member + a handler implementing this protocol + a typed content model; the
    allow-list is derived from the registry and the manager needs no
    category-specific edits.
    """

    category: PersonalNotificationCategory

    def is_enabled(self, ctx: RequestHandlerContext) -> bool:
        """Whether this request category is enabled for the submitting request's host."""
        ...

    def stamp_content(
        self, content: AnyNotificationCreateContent, ctx: RequestHandlerContext
    ) -> AnyInternalNotificationContent:
        """Rewrite the client-supplied content server-side (e.g. stamp the requester email).

        Must raise ``RequestParameterInvalidException`` when the content type does
        not match this handler's category, so mismatched category/content
        submissions are rejected instead of persisted.
        """
        ...

    def resolve_recipients(self, ctx: RequestHandlerContext) -> NotificationRecipients:
        """Resolve who the request is delivered to (typically the instance admins)."""
        ...

    def build_confirmation(
        self, ctx: RequestHandlerContext, admin_request: NotificationCreateRequest
    ) -> NotificationCreateRequest | None:
        """Optionally derive the submitter's confirmation copy, or None for no copy."""
        ...


class ToolInstallationRequestHandler:
    """Handler for ``tool_installation_request`` user submissions.

    Delivers the request to all instance admins and, when the submitter is not an
    admin, produces a confirmation copy for the submitter.
    """

    category = PersonalNotificationCategory.tool_installation_request

    def is_enabled(self, ctx: RequestHandlerContext) -> bool:
        # The option is per-host configurable. ``/api/configuration`` resolves it
        # against the request host (so the client hides the form on a host where
        # it is disabled); the server-side gate must do the same, or a per-host
        # disable would only hide the button while the API stays open.
        if ctx.host:
            return bool(ctx.config.config_value_for_host("enable_tool_installation_request_form", ctx.host))
        return bool(ctx.config.enable_tool_installation_request_form)

    def stamp_content(
        self, content: AnyNotificationCreateContent, ctx: RequestHandlerContext
    ) -> AnyInternalNotificationContent:
        if not isinstance(content, ToolInstallationRequestCreateContent):
            raise RequestParameterInvalidException(
                "The notification content does not match the tool_installation_request category."
            )
        workflow_id, workflow_name = self._accessible_workflow(content.workflow_id, ctx)
        # Promote the request (create) content to the stored content model and
        # stamp the requester's real email server-side (never trust the client).
        # is_confirmation is forced False on the admin-facing copy; build_confirmation
        # below decides which copy is the confirmation.
        # model_construct reuses the already-validated field values instead of
        # re-running every sanitizer and bound check on them.
        return StoredToolInstallationRequestContent.model_construct(
            **{**dict(content), "workflow_id": workflow_id},
            requester_email=ctx.sender.email,
            is_confirmation=False,
            workflow_name=workflow_name,
        )

    @staticmethod
    def _accessible_workflow(workflow_id: str | None, ctx: RequestHandlerContext) -> tuple[str | None, str | None]:
        """Canonical encoded id and name of the referenced stored workflow, verified accessible to the submitter.

        The id is rendered as a run link and the name is shown in the admin-facing
        notification, so it must name a ``StoredWorkflow`` (not a ``Workflow``
        instance id, which the run page also accepts) that the submitter can
        access -- otherwise a submitter could make the admin email display and
        link another user's private workflow. One error message for every
        failure mode, so an inaccessible id is not distinguishable from a
        missing one.
        """
        if workflow_id is None:
            return None, None
        try:
            stored_workflow = ctx.workflows_manager.get_stored_accessible_workflow(
                ctx.trans, workflow_id, by_stored_id=True
            )
        except (MalformedId, ObjectNotFound, ItemAccessibilityException):
            raise RequestParameterInvalidException("workflow_id does not refer to a workflow accessible to you.")
        return ctx.trans.security.encode_id(stored_workflow.id), stored_workflow.name

    def resolve_recipients(self, ctx: RequestHandlerContext) -> NotificationRecipients:
        admin_users = ctx.user_manager.admins()
        if not admin_users:
            raise ServerNotConfiguredForRequest("No admin users are configured on this Galaxy instance.")
        return NotificationRecipients(user_ids=[u.id for u in admin_users])

    def build_confirmation(
        self, ctx: RequestHandlerContext, admin_request: NotificationCreateRequest
    ) -> NotificationCreateRequest | None:
        admin_user_ids = set(admin_request.recipients.user_ids)
        if ctx.sender.id in admin_user_ids:
            # An admin submitter already receives the admin-facing request -- no separate copy.
            return None
        notification_data = admin_request.notification
        content = notification_data.content
        # stamp_content rejects any other content type for this category, so the
        # admin request always carries the stored model; assert only narrows the type.
        assert isinstance(content, StoredToolInstallationRequestContent)
        confirmation_content = content.model_copy(update={"is_confirmation": True})
        confirmation_notification = notification_data.model_copy(update={"content": confirmation_content})
        return admin_request.model_copy(
            update={
                "notification": confirmation_notification,
                "recipients": NotificationRecipients(user_ids=[ctx.sender.id]),
            }
        )


class NotificationRequestManager:
    """Turns a user's notification submission into the requests to send.

    The registry of per-category handlers lives on the instance, so the
    user allow-list is derived from it and the two cannot drift apart. To add a
    new user-submittable request type, register its handler in
    :meth:`_build_handlers`.
    """

    def __init__(
        self,
        config: GalaxyAppConfiguration,
        user_manager: UserManager,
        workflows_manager: WorkflowsManager,
    ):
        self.config = config
        self.user_manager = user_manager
        self.workflows_manager = workflows_manager
        self._handlers: dict[NotificationCategory, NotificationRequestHandler] = self._build_handlers()

    @staticmethod
    def _build_handlers() -> dict[NotificationCategory, NotificationRequestHandler]:
        return {handler.category: handler for handler in (ToolInstallationRequestHandler(),)}

    @property
    def user_allowed_categories(self) -> frozenset[NotificationCategory]:
        """Categories a non-admin user may submit."""
        return frozenset(self._handlers)

    def build_user_sender_requests(
        self,
        sender_context: SessionRequestContext,
        payload: NotificationCreateRequestBody,
        galaxy_url: str | None,
    ) -> list[NotificationCreateRequest]:
        """Validate and rewrite a user notification submission.

        For admin users sending non-user-allowed categories, passes through the payload as-is.
        For user-allowed request categories (non-admins, or admins sending such a category),
        validates the category and dispatches to the per-category ``NotificationRequestHandler``
        which rewrites recipients/content server-side and may produce a confirmation copy.

        The first returned request is the admin-facing one; a confirmation copy, if
        any, follows it.
        """
        category = payload.notification.category
        # Envelope/content category agreement is enforced by the
        # NotificationCreateData model validator when the body is parsed.

        # Admin sending arbitrary category notification: pass through unchanged.
        # The data is promoted to the internal model so the request matches its
        # declared (full content union) type on the Celery round-trip.
        if sender_context.user_is_admin and category not in self._handlers:
            return [
                NotificationCreateRequest.model_construct(
                    notification=InternalNotificationCreateData.model_construct(**dict(payload.notification)),
                    recipients=payload.recipients,
                    galaxy_url=galaxy_url,
                )
            ]

        # All other cases: validate and dispatch to the request handler
        sender = sender_context.user
        if sender_context.anonymous or sender is None:
            raise AuthenticationRequired("You must be logged in to submit a notification.")

        handler = self._handlers.get(category)
        if handler is None:
            raise AdminRequiredException("Only administrators can send notifications of this category.")

        ctx = RequestHandlerContext(
            trans=sender_context,
            sender=sender,
            host=sender_context.host,
            config=self.config,
            user_manager=self.user_manager,
            workflows_manager=self.workflows_manager,
        )
        if not handler.is_enabled(ctx):
            # A disabled feature is a configuration state, not a permission
            # problem, so it is reported as such rather than as "admin required".
            # Note: pydantic validates the category union/Literal fields to plain
            # strings, so interpolating `category` yields the bare value.
            raise ConfigDoesNotAllowException(f"{category} notifications are disabled on this Galaxy instance.")

        content = handler.stamp_content(payload.notification.content, ctx)

        # Like the stamped content fields, the envelope of a user-submitted
        # request is server-controlled: source and variant are fixed (a client
        # must not escalate to e.g. `urgent`, which bypasses channel opt-outs),
        # and the timing fields are not client-settable -- publication is
        # immediate and expiration falls back to the default retention period
        # applied by the notification model.
        notification_data = InternalNotificationCreateData.model_construct(
            source=f"{category}_form",
            category=payload.notification.category,
            variant=NotificationVariant.info,
            content=content,
            publication_time=None,
            expiration_time=None,
        )

        # Admin-facing request: delivered to the handler-resolved recipients (the
        # submitter receives it too if they are among them, e.g. an admin).
        admin_request = NotificationCreateRequest.model_construct(
            notification=notification_data,
            recipients=handler.resolve_recipients(ctx),
            galaxy_url=galaxy_url,
        )
        requests = [admin_request]

        # Optional submitter confirmation copy. The handler returns None when no
        # copy is appropriate (e.g. the submitter already receives the request).
        confirmation = handler.build_confirmation(ctx, admin_request)
        if confirmation is not None:
            requests.append(confirmation)

        return requests

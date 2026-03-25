import logging
from datetime import (
    timedelta,
    timezone,
)
from typing import Optional

from pydantic import Field

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import (
    AuthenticationRequired,
    ServerNotConfiguredForRequest,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.notification import NotificationManager
from galaxy.managers.users import UserManager
from galaxy.schema.notifications import (
    NotificationCreateData,
    NotificationCreateRequest,
    NotificationRecipients,
    NotificationVariant,
    PersonalNotificationCategory,
    ToolRequestNotificationContent,
)
from galaxy.schema.schema import Model
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class ToolRequestFormData(Model):
    """The data submitted with the Tool Request Form."""

    tool_name: str = Field(..., title="Tool name", description="The name of the requested tool.")
    tool_url: Optional[str] = Field(
        None, title="Tool URL", description="Homepage or repository URL for the requested tool."
    )
    description: str = Field(
        ..., title="Description", description="Short description of the tool and its scientific use case."
    )
    scientific_domain: Optional[str] = Field(
        None, title="Scientific domain", description="The scientific domain for the requested tool."
    )
    requested_version: Optional[str] = Field(
        None, title="Requested version", description="The version of the tool being requested."
    )
    conda_available: Optional[bool] = Field(
        None, title="Conda available", description="Whether a Conda package for this tool is available."
    )
    test_data_available: Optional[bool] = Field(
        None, title="Test data available", description="Whether test data for this tool is available."
    )
    requester_name: str = Field(..., title="Requester name", description="The name of the person requesting the tool.")
    requester_email: Optional[str] = Field(
        None, title="Requester email", description="The email address of the requester for follow-up."
    )
    requester_affiliation: Optional[str] = Field(
        None, title="Requester affiliation", description="The affiliation/lab of the requester."
    )


class ToolRequestFormService(ServiceBase):
    """Service for handling Tool Request Form submissions.

    When a user submits a tool request, a notification is sent to all admin users
    via Galaxy's notification system so that admins can review and act on the request.
    """

    def __init__(
        self,
        security: IdEncodingHelper,
        config: GalaxyAppConfiguration,
        notification_manager: NotificationManager,
        user_manager: UserManager,
    ):
        super().__init__(security)
        self.config = config
        self.notification_manager = notification_manager
        self.user_manager = user_manager

    def submit_tool_request(self, trans: ProvidesUserContext, payload: ToolRequestFormData) -> None:
        """Submit a tool installation request to the instance admins.

        Sends a notification to all admin users with the submitted tool request details.

        :raises ServerNotConfiguredForRequest: if the tool request form is not enabled.
        :raises AuthenticationRequired: if the user is not authenticated.
        """
        if not self.config.enable_tool_request_form:
            raise ServerNotConfiguredForRequest("The tool request form is not enabled in the configuration.")

        if trans.anonymous:
            raise AuthenticationRequired("You must be logged in to submit a tool request.")

        if not self.config.enable_notification_system:
            raise ServerNotConfiguredForRequest("The notification system must be enabled to use the tool request form.")

        admin_users = self.user_manager.admins()
        if not admin_users:
            raise ServerNotConfiguredForRequest("No admin users are configured on this Galaxy instance.")

        content = ToolRequestNotificationContent(
            tool_name=payload.tool_name,
            tool_url=payload.tool_url,
            description=payload.description,
            scientific_domain=payload.scientific_domain,
            requested_version=payload.requested_version,
            conda_available=payload.conda_available,
            test_data_available=payload.test_data_available,
            requester_name=payload.requester_name,
            requester_email=payload.requester_email,
            requester_affiliation=payload.requester_affiliation,
        )

        import datetime

        now = datetime.datetime.now(tz=timezone.utc).replace(tzinfo=None)
        expiration_time = now + timedelta(days=180)

        notification_data = NotificationCreateData(
            source="tool_request_form",
            category=PersonalNotificationCategory.tool_request,
            variant=NotificationVariant.info,
            content=content,
            expiration_time=expiration_time,
        )

        recipients = NotificationRecipients(
            user_ids=[user.id for user in admin_users],
        )

        galaxy_url = str(trans.url_builder("/", qualified=True)).rstrip("/") if trans.url_builder else None

        request = NotificationCreateRequest(
            notification=notification_data,
            recipients=recipients,
            galaxy_url=galaxy_url,
        )

        self.notification_manager.send_notification_to_recipients(request)
        log.info(
            "Tool request '%s' submitted by user %s, notified %d admin(s).",
            payload.tool_name,
            trans.user.username if trans.user else "unknown",
            len(admin_users),
        )

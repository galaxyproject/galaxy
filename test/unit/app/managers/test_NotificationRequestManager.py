from unittest.mock import (
    MagicMock,
    patch,
)

import pytest
from sqlalchemy.exc import OperationalError

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import (
    AdminRequiredException,
    AuthenticationRequired,
    ConfigDoesNotAllowException,
    RequestParameterInvalidException,
    ServerNotConfiguredForRequest,
)
from galaxy.managers.notification import NotificationManager
from galaxy.managers.notification_requests import NotificationRequestManager
from galaxy.managers.sse import SSEConnectionManager
from galaxy.managers.tools import DynamicToolManager
from galaxy.managers.workflows import WorkflowsManager
from galaxy.model import StoredWorkflow
from galaxy.schema.fields import Security
from galaxy.schema.notifications import (
    NotificationCreatedResponse,
    NotificationCreateRequestBody,
    NotificationVariant,
    StoredToolInstallationRequestContent,
)
from galaxy.webapps.galaxy.services.notifications import NotificationService
from .base import BaseTestCase

REQUEST_HOST = "usegalaxy.example:8080"


def _tool_request_body(**notification_overrides) -> NotificationCreateRequestBody:
    notification = {
        "source": "client-chosen",
        "category": "tool_installation_request",
        "variant": "info",
        "content": {
            "category": "tool_installation_request",
            "tools": [{"name": "bwa", "requested_version": "0.7.17"}],
            "additional_remarks": "needed for the mapping workflow",
        },
    }
    notification.update(notification_overrides)
    return NotificationCreateRequestBody.model_validate(
        {"recipients": {"user_ids": [], "group_ids": [], "role_ids": []}, "notification": notification}
    )


def _message_body(recipient_id: str) -> NotificationCreateRequestBody:
    return NotificationCreateRequestBody.model_validate(
        {
            "recipients": {"user_ids": [recipient_id], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "admin",
                "category": "message",
                "variant": "urgent",
                "content": {"category": "message", "subject": "s", "message": "m"},
            },
        }
    )


class NotificationRequestTestCase(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.config = MagicMock(spec=GalaxyAppConfiguration)
        self.config.enable_tool_installation_request_form = True
        self.per_host_flags: dict[str, bool] = {}
        self.config.config_value_for_host.side_effect = lambda option, host: self.per_host_flags.get(
            host, getattr(self.config, option)
        )
        self.request_manager = NotificationRequestManager(
            self.config, self.user_manager, WorkflowsManager(self.app, DynamicToolManager(self.app))
        )
        # Request bodies carry encoded ids, decoded through the process-global Security.security.
        self._security_patch = patch.object(Security, "security", self.trans.security, create=True)
        self._security_patch.start()

    def tearDown(self):
        self._security_patch.stop()
        super().tearDown()

    def set_up_trans(self):
        super().set_up_trans()
        self.mock_trans.host = REQUEST_HOST
        self.submitter = self.user_manager.create(
            email="submitter@user.email", username="submitter", password="password"
        )
        self._act_as(self.submitter, admin=False)

    def _act_as(self, user, admin: bool):
        self.trans.set_user(user)
        self.mock_trans.user_is_admin = admin
        self.mock_trans.anonymous = False


class TestNotificationRequestManager(NotificationRequestTestCase):
    def _build(self, body=None):
        return self.request_manager.build_user_sender_requests(self.trans, body or _tool_request_body(), "https://gx")

    def test_user_request_is_delivered_to_admins_with_a_confirmation_copy(self):
        admin_request, confirmation = self._build()

        assert admin_request.recipients.user_ids == [self.admin_user.id]
        assert admin_request.galaxy_url == "https://gx"
        content = admin_request.notification.content
        assert isinstance(content, StoredToolInstallationRequestContent)
        assert content.requester_email == self.submitter.email
        assert content.is_confirmation is False
        assert content.tools[0].name == "bwa"

        assert confirmation.recipients.user_ids == [self.submitter.id]
        confirmation_content = confirmation.notification.content
        assert isinstance(confirmation_content, StoredToolInstallationRequestContent)
        assert confirmation_content.is_confirmation is True
        assert confirmation_content.requester_email == self.submitter.email

    def test_envelope_is_server_controlled(self):
        admin_request, _ = self._build(_tool_request_body(variant="urgent", source="spoofed"))
        notification = admin_request.notification
        assert notification.variant == NotificationVariant.info
        assert notification.source == "tool_installation_request_form"
        assert notification.publication_time is None
        assert notification.expiration_time is None

    def test_admin_submitter_gets_no_confirmation_copy(self):
        self._act_as(self.admin_user, admin=True)
        requests = self._build()
        assert len(requests) == 1
        assert requests[0].recipients.user_ids == [self.admin_user.id]

    def test_admin_sending_other_categories_passes_through(self):
        self._act_as(self.admin_user, admin=True)
        body = _message_body(self.trans.security.encode_id(self.submitter.id))
        (request,) = self._build(body)
        assert request.recipients == body.recipients
        assert request.notification.variant == NotificationVariant.urgent
        assert request.notification.source == "admin"

    def test_non_admin_cannot_send_other_categories(self):
        with pytest.raises(AdminRequiredException):
            self._build(_message_body(self.trans.security.encode_id(self.admin_user.id)))

    def test_anonymous_cannot_submit(self):
        self.trans.set_user(None)
        self.mock_trans.anonymous = True
        with pytest.raises(AuthenticationRequired):
            self._build()

    def test_disabled_feature_is_a_config_restriction(self):
        self.config.enable_tool_installation_request_form = False
        with pytest.raises(ConfigDoesNotAllowException):
            self._build()

    def test_per_host_disable_gates_the_submitting_host_only(self):
        self.per_host_flags[REQUEST_HOST] = False
        with pytest.raises(ConfigDoesNotAllowException):
            self._build()
        self.mock_trans.host = "other.example"
        assert len(self._build()) == 2

    def test_inaccessible_workflow_id_is_rejected(self):
        with pytest.raises(RequestParameterInvalidException):
            self._build(
                _tool_request_body(
                    content={
                        "category": "tool_installation_request",
                        "tools": [{"name": "bwa"}],
                        "workflow_id": "not-an-encoded-id",
                    }
                )
            )

    def test_workflow_name_is_stamped_on_a_single_line(self):
        stored_workflow = StoredWorkflow(user=self.submitter, name="Mapping\nRequested by: ceo@evil.example")
        self.trans.sa_session.add(stored_workflow)
        self.trans.sa_session.commit()
        workflow_id = self.trans.security.encode_id(stored_workflow.id)
        admin_request, _ = self._build(
            _tool_request_body(
                content={
                    "category": "tool_installation_request",
                    "tools": [{"name": "bwa"}],
                    "workflow_id": workflow_id,
                }
            )
        )
        content = admin_request.notification.content
        assert isinstance(content, StoredToolInstallationRequestContent)
        assert content.workflow_id == workflow_id
        assert content.workflow_name == "Mapping Requested by: ceo@evil.example"

    def test_no_admins_is_a_server_configuration_error(self):
        self.admin_user.deleted = True
        self.trans.sa_session.commit()
        with pytest.raises(ServerNotConfiguredForRequest):
            self._build()


class _ConfirmationFailingNotificationManager(NotificationManager):
    def send_notification_internal(self, request, force_sync=False):
        content = request.notification.content
        if isinstance(content, StoredToolInstallationRequestContent) and content.is_confirmation:
            raise OperationalError("INSERT INTO notification", {}, Exception("database is locked"))
        return super().send_notification_internal(request, force_sync=force_sync)


class TestNotificationRequestDelivery(NotificationRequestTestCase):
    def test_failed_confirmation_still_delivers_the_admin_request(self):
        self.app.config.enable_notification_system = True
        notification_manager = _ConfirmationFailingNotificationManager(self.trans.sa_session, self.app.config)
        service = NotificationService(notification_manager, SSEConnectionManager(), self.request_manager)

        response = service.send_notification(self.trans, _tool_request_body())

        assert isinstance(response, NotificationCreatedResponse)
        assert response.total_notifications_sent == 1
        (admin_notification,) = notification_manager.get_user_notifications(self.admin_user)
        assert response.notification.id == self.trans.security.encode_id(admin_notification.id)
        assert notification_manager.get_user_notifications(self.submitter) == []

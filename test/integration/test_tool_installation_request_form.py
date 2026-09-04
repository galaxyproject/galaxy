"""Integration tests for the tool-installation-request-form feature (routed via POST /api/notifications)."""

import json
import os
import re
from typing import ClassVar

from galaxy_test.base.api_util import ADMIN_TEST_USER
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase

TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY = {
    "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
    "notification": {
        "source": "tool_installation_request_form",
        "category": "tool_installation_request",
        "variant": "info",
        "content": {
            "category": "tool_installation_request",
            "tools": [
                {
                    "name": "FastQC",
                    "tool_shed_id": None,
                    "tool_url": "https://github.com/s-andrews/FastQC",
                    "description": "Quality control tool for high-throughput sequencing data.",
                    "scientific_domain": "Genomics",
                    "requested_version": "0.12.1",
                }
            ],
            "additional_remarks": "Would be great for the genomics team.",
        },
    },
}


class ToolInstallationRequestFormIntegrationBase(IntegrationTestCase):
    """Base class with configuration for tool installation request form tests."""

    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_tool_installation_request_form"] = True
        config["enable_celery_tasks"] = False

    def setUp(self):
        super().setUp()
        # Ensure the admin user exists in the database so notifications can be sent to them.
        self._setup_user(ADMIN_TEST_USER)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)


class TestToolInstallationRequestFormIntegration(ToolInstallationRequestFormIntegrationBase):
    def test_anonymous_user_cannot_submit(self):
        """Anonymous users should receive 403 (AuthenticationRequired)."""
        with self._different_user(anon=True):
            response = self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 403)

    def test_registered_user_can_submit(self):
        """A registered user can successfully submit a tool installation request via POST /api/notifications."""
        user = self._setup_user("tool_installation_request_submitter@galaxy.test")
        with self._different_user(user["email"]):
            response = self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 200)
            data = response.json()
            assert "notification" in data
            assert data["notification"]["id"]

    def test_admin_receives_notification_after_submission(self):
        """After a user submits a tool installation request the admin should have a new notification."""
        user = self._setup_user("tool_installation_request_sender@galaxy.test")
        with self._different_user(user["email"]):
            response = self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 200)

        # Admin should now have a tool_installation_request notification
        with self._different_user(ADMIN_TEST_USER):
            notifications = self._get("notifications").json()
        tool_installation_request_notifications = [
            n for n in notifications if n.get("category") == "tool_installation_request"
        ]
        assert (
            len(tool_installation_request_notifications) >= 1
        ), f"Expected at least one tool_installation_request notification for admin, got: {notifications}"
        # The admin-facing copy must not be flagged as a confirmation.
        assert all(
            not n.get("content", {}).get("is_confirmation", False) for n in tool_installation_request_notifications
        ), "Admin-facing tool request notification must have is_confirmation=False"

    def test_sender_receives_notification_too(self):
        """The submitter should also receive the notification in their own inbox."""
        user = self._setup_user("tool_installation_request_sender2@galaxy.test")
        with self._different_user(user["email"]):
            self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            notifications = self._get("notifications").json()
        tool_installation_request_notifications = [
            n for n in notifications if n.get("category") == "tool_installation_request"
        ]
        assert (
            len(tool_installation_request_notifications) >= 1
        ), f"Expected sender to receive the notification, got: {notifications}"
        # The submitter's copy must be the confirmation (is_confirmation=True).
        assert any(
            n.get("content", {}).get("is_confirmation", False) for n in tool_installation_request_notifications
        ), "Sender's tool request notification must have is_confirmation=True"

    def test_admin_submitter_receives_only_admin_copy(self):
        """An admin who submits their own request gets the admin copy, not a separate confirmation."""
        with self._different_user(ADMIN_TEST_USER):
            response = self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 200)
            notifications = self._get("notifications").json()
        tool_installation_request_notifications = [
            n for n in notifications if n.get("category") == "tool_installation_request"
        ]
        assert tool_installation_request_notifications, "Expected the admin to receive their own request"
        assert all(
            not n.get("content", {}).get("is_confirmation", False) for n in tool_installation_request_notifications
        ), "An admin submitter should not receive a separate confirmation copy"

    def test_requester_email_overridden_server_side(self):
        """Server-stamped content fields must override any client-supplied values.

        requester_email must be the user's real email, and is_confirmation must be
        False on the admin-facing copy -- never trusting a client-supplied True that
        would render the confirmation template/subject to admins.
        """
        user = self._setup_user("tool_installation_request_email_check@galaxy.test")
        payload_with_spoofed_email = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "tool_installation_request_form",
                "category": "tool_installation_request",
                "variant": "info",
                "content": {
                    "category": "tool_installation_request",
                    "tools": [
                        {
                            "name": "FastQC",
                            "tool_shed_id": None,
                            "tool_url": "https://github.com/s-andrews/FastQC",
                            "description": "Quality control tool for high-throughput sequencing data.",
                            "scientific_domain": "Genomics",
                            "requested_version": "0.12.1",
                        }
                    ],
                    "additional_remarks": "Would be great for the genomics team.",
                    "requester_email": "spoofed@example.com",
                    "is_confirmation": True,
                },
            },
        }
        with self._different_user(user["email"]):
            self._post("notifications", data=payload_with_spoofed_email, json=True)
            notifications = self._get("notifications").json()
        tool_installation_request_notifications = [
            n for n in notifications if n.get("category") == "tool_installation_request"
        ]
        assert tool_installation_request_notifications, "Expected at least one tool_installation_request notification"
        content = tool_installation_request_notifications[0]["content"]
        assert (
            content["requester_email"] == user["email"]
        ), f"requester_email should be {user['email']!r}, got {content['requester_email']!r}"

        # The admin-facing copy must have is_confirmation=False even though the
        # client sent True -- a client-supplied True must never reach admins and
        # render the confirmation template/subject to them.
        with self._different_user(ADMIN_TEST_USER):
            admin_notifications = self._get("notifications").json()
        admin_copies = [
            n
            for n in admin_notifications
            if n.get("category") == "tool_installation_request"
            and not n.get("content", {}).get("is_confirmation", False)
        ]
        assert admin_copies, "Expected an admin-facing tool request notification with is_confirmation=False"
        # This request's admin copy must carry the server-stamped requester_email.
        this_request_admin_copies = [n for n in admin_copies if n["content"].get("requester_email") == user["email"]]
        assert (
            this_request_admin_copies
        ), "Expected the admin-facing copy of this request to carry the server-stamped requester_email"

    def test_client_supplied_recipients_ignored(self):
        """The server must override recipients regardless of what the client sends."""
        user = self._setup_user("tool_installation_request_recipients_check@galaxy.test")
        ignored_recipient = self._setup_user("tool_installation_request_ignored_recipient@galaxy.test")
        payload_with_recipients = {
            "recipients": {"user_ids": [ignored_recipient["id"]], "group_ids": [], "role_ids": []},
            "notification": TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY["notification"],
        }
        with self._different_user(user["email"]):
            response = self._post("notifications", data=payload_with_recipients, json=True)
            # Server accepts the request and overrides recipients — should still succeed
            self._assert_status_code_is(response, 200)

        with self._different_user(ignored_recipient["email"]):
            notifications = self._get("notifications").json()
        tool_installation_request_notifications = [
            n for n in notifications if n.get("category") == "tool_installation_request"
        ]
        assert (
            tool_installation_request_notifications == []
        ), "Client-supplied recipients must be ignored for user submissions"

    def test_mismatched_category_and_content_rejected(self):
        """A tool_installation_request submission with non-tool-request content is rejected."""
        user = self._setup_user("tool_installation_request_mismatch@galaxy.test")
        mismatched_payload = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "tool_installation_request_form",
                "category": "tool_installation_request",
                "variant": "info",
                "content": {
                    "category": "message",
                    "subject": "Not a tool request",
                    "message": "This content does not match the declared category",
                },
            },
        }
        with self._different_user(user["email"]):
            response = self._post("notifications", data=mismatched_payload, json=True)
            self._assert_status_code_is(response, 400)

    def test_admin_mismatched_category_and_content_rejected(self):
        """The envelope/content category check also applies to the admin passthrough path."""
        mismatched_payload = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "test",
                "category": "message",
                "variant": "info",
                "content": {
                    "category": "tool_installation_request",
                    "tools": [{"name": "FastQC"}],
                },
            },
        }
        with self._different_user(ADMIN_TEST_USER):
            response = self._post("notifications", data=mismatched_payload, json=True)
            self._assert_status_code_is(response, 400)

    def test_whitespace_only_tool_identifier_rejected(self):
        """A tool entry whose only identifier is whitespace fails validation."""
        user = self._setup_user("tool_installation_request_blank_id@galaxy.test")
        payload = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "tool_installation_request_form",
                "category": "tool_installation_request",
                "variant": "info",
                "content": {
                    "category": "tool_installation_request",
                    "tools": [{"name": "   "}],
                },
            },
        }
        with self._different_user(user["email"]):
            response = self._post("notifications", data=payload, json=True)
            assert response.status_code in (400, 422), response.text

    def test_control_characters_sanitized_and_envelope_stamped(self):
        """Newlines in tool fields are collapsed, and the notification envelope
        (source, variant, expiration) is server-controlled regardless of the payload."""
        user = self._setup_user("tool_installation_request_envelope@galaxy.test")
        payload = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "client-chosen-source",
                "category": "tool_installation_request",
                "variant": "urgent",
                "expiration_time": "2000-01-01T00:00:00",
                "content": {
                    "category": "tool_installation_request",
                    "tools": [{"name": "FastQC\nEvil"}],
                },
            },
        }
        with self._different_user(user["email"]):
            response = self._post("notifications", data=payload, json=True)
            self._assert_status_code_is(response, 200)
            notification = response.json()["notification"]
        assert notification["variant"] == "info", "variant must be server-stamped, not client-escalated"
        assert notification["source"] == "tool_installation_request_form"
        assert notification["expiration_time"] != "2000-01-01T00:00:00"
        assert notification["content"]["tools"][0]["name"] == "FastQC Evil"

    def test_non_admin_cannot_send_disallowed_category(self):
        """Non-admin users may not send 'message' category notifications."""
        user = self._setup_user("tool_installation_request_category_check@galaxy.test")
        message_payload = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "test",
                "category": "message",
                "variant": "info",
                "content": {
                    "category": "message",
                    "subject": "Hello",
                    "message": "This should be blocked",
                },
            },
        }
        with self._different_user(user["email"]):
            response = self._post("notifications", data=message_payload, json=True)
            self._assert_status_code_is(response, 403)

    def test_minimal_payload_succeeds(self):
        """Only required content fields (tool_names, description) should be enough."""
        user = self._setup_user("tool_installation_request_minimal@galaxy.test")
        minimal_payload = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "tool_installation_request_form",
                "category": "tool_installation_request",
                "variant": "info",
                "content": {
                    "category": "tool_installation_request",
                    "tools": [
                        {
                            "name": "Samtools",
                            "tool_shed_id": None,
                            "tool_url": None,
                            "description": "Tools for manipulating alignments in SAM format.",
                            "scientific_domain": None,
                            "requested_version": None,
                        }
                    ],
                },
            },
        }
        with self._different_user(user["email"]):
            response = self._post("notifications", data=minimal_payload, json=True)
            self._assert_status_code_is(response, 200)

    def test_workflow_install_request_with_tool_names(self):
        """Submit a request that includes workflow context (multiple tool_names + workflow_id)."""
        user = self._setup_user("tool_installation_request_workflow@galaxy.test")
        workflow_payload = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "tool_installation_request_form",
                "category": "tool_installation_request",
                "variant": "info",
                "content": {
                    "category": "tool_installation_request",
                    "tools": [
                        {
                            "name": None,
                            "tool_shed_id": "toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17",
                            "tool_url": None,
                            "description": "These tools are required by My Analysis workflow.",
                            "scientific_domain": None,
                            "requested_version": None,
                        },
                        {
                            "name": None,
                            "tool_shed_id": "toolshed.g2.bx.psu.edu/repos/devteam/samtools/samtools/1.13",
                            "tool_url": None,
                            "description": None,
                            "scientific_domain": None,
                            "requested_version": None,
                        },
                    ],
                    "workflow_id": "encoded-workflow-id-abc",
                },
            },
        }
        with self._different_user(user["email"]):
            response = self._post("notifications", data=workflow_payload, json=True)
            self._assert_status_code_is(response, 200)

        with self._different_user(ADMIN_TEST_USER):
            notifications = self._get("notifications").json()
        workflow_tool_notifications = [
            n
            for n in notifications
            if n.get("category") == "tool_installation_request"
            and n.get("content", {}).get("workflow_id") == "encoded-workflow-id-abc"
        ]
        assert (
            len(workflow_tool_notifications) >= 1
        ), f"Expected at least one tool_installation_request notification with workflow_id, got: {notifications}"
        content = workflow_tool_notifications[0]["content"]
        assert content["workflow_id"] == "encoded-workflow-id-abc"
        assert len(content["tools"]) == 2


class TestToolInstallationRequestFormEmailDeliveryIntegration(ToolInstallationRequestFormIntegrationBase):
    email_directory: ClassVar[str]

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.email_directory = cls._test_driver.mkdtemp()
        config["enable_celery_tasks"] = True
        config["email_from"] = "galaxy-no-reply@example.com"
        config["smtp_server"] = f"mock_emails_to_path://{cls.email_directory}/email.json"

    def test_submission_creates_notification_without_sending_admin_email_synchronously(self):
        """Tool installation requests return the notification synchronously but leave email delivery to Celery."""
        user = self._setup_user("tool_installation_request_email_delivery@galaxy.test")
        with self._different_user(user["email"]):
            update_request = {
                "preferences": {
                    "tool_installation_request": {
                        "enabled": True,
                        "channels": {"push": True, "email": False},
                    }
                }
            }
            update_response = self._put("notifications/preferences", data=update_request, json=True)
            self._assert_status_code_is_ok(update_response)

            response = self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 200)
            data = response.json()
            task_id = data["id"]
            assert task_id

            self.dataset_populator.wait_on_task_id(task_id)

            # verify the notification was created
            notifications = self._get("notifications").json()
            tool_installation_request_notifications = [
                n for n in notifications if n.get("category") == "tool_installation_request"
            ]
            assert len(tool_installation_request_notifications) >= 1

        assert not os.path.exists(os.path.join(self.email_directory, "email.json"))


class TestToolInstallationRequestFormEmailContentIntegration(ToolInstallationRequestFormIntegrationBase):
    """End-to-end rendering/delivery of the tool-request email via the real dispatch path."""

    email_directory: ClassVar[str]

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.email_directory = cls._test_driver.mkdtemp()
        # The email channel is only registered when async (Celery) processing is on.
        config["enable_celery_tasks"] = True
        config["email_from"] = "galaxy-no-reply@example.com"
        config["smtp_server"] = f"mock_emails_to_path://{cls.email_directory}/email.json"

    def test_admin_email_renders_requested_tool_fields(self):
        """The admin email subject/body render the requested tools from the persisted content.

        An admin submits their own request so exactly one (admin-facing) email is
        produced, making the mock email file content deterministic.
        """
        with self._different_user(ADMIN_TEST_USER):
            response = self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 200)
            self.dataset_populator.wait_on_task_id(response.json()["id"])

        # Emails are delivered by the periodic background dispatcher, not during
        # the request; run it directly to render and send the pending email.
        dispatched = self._app.notification_manager.dispatch_pending_notifications_via_channels()
        assert dispatched >= 1

        email_path = os.path.join(self.email_directory, "email.json")
        assert os.path.exists(email_path), "Expected the admin tool-request email to be delivered"
        with open(email_path) as f:
            email = json.load(f)
        assert email["to"] == ADMIN_TEST_USER
        assert email["subject"] == "[Galaxy] Tool installation request: FastQC"
        body = email["body"]
        # Field rows start at column 0 with their value on the same line; the
        # exact label padding is presentation, so it is not pinned here.
        assert re.search(r"^Tool: +FastQC$", body, re.MULTILINE)
        assert re.search(r"^URL: +https://github\.com/s-andrews/FastQC$", body, re.MULTILINE)
        assert re.search(r"^Domain: +Genomics$", body, re.MULTILINE)
        assert re.search(r"^Version: +0\.12\.1$", body, re.MULTILINE)
        assert re.search(r"^Remarks: +Would be great for the genomics team\.$", body, re.MULTILINE)
        assert re.search(rf"^Requested by: {re.escape(ADMIN_TEST_USER)}$", body, re.MULTILINE)
        # No stray blank lines within the rendered field block: exactly one blank
        # line before it, and consecutive field lines with no gaps.
        assert "\n\nTool:" in body
        assert "\n\n\nTool:" not in body
        assert re.search(r"^Version: +0\.12\.1\nRemarks:", body, re.MULTILINE)
        html = email["html"]
        assert "FastQC" in html and "Genomics" in html


class TestToolInstallationRequestFormDisabledIntegration(IntegrationTestCase):
    """Tests for when the tool installation request form feature is disabled."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_tool_installation_request_form"] = False
        config["enable_celery_tasks"] = False

    def test_disabled_config_returns_error(self):
        """When tool_installation_request_form is disabled, non-admin submissions should be denied."""
        user = self._setup_user("tool_installation_request_disabled@galaxy.test")
        with self._different_user(user["email"]):
            response = self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 403)

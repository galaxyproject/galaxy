"""Integration tests for the tool-request-form feature (routed via POST /api/notifications)."""

from galaxy_test.base.api_util import ADMIN_TEST_USER
from galaxy_test.driver.integration_util import IntegrationTestCase

TOOL_REQUEST_NOTIFICATION_BODY = {
    "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
    "notification": {
        "source": "tool_request_form",
        "category": "tool_request",
        "variant": "info",
        "content": {
            "category": "tool_request",
            "tool_names": ["FastQC"],
            "tool_url": "https://github.com/s-andrews/FastQC",
            "description": "Quality control tool for high-throughput sequencing data.",
            "scientific_domain": "Genomics",
            "requested_version": "0.12.1",
            "additional_remarks": "Would be great for the genomics team.",
        },
    },
}


class ToolRequestFormIntegrationBase(IntegrationTestCase):
    """Base class with configuration for tool request form tests."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_tool_request_form"] = True
        config["enable_celery_tasks"] = False

    def setUp(self):
        super().setUp()
        # Ensure the admin user exists in the database so notifications can be sent to them.
        self._setup_user(ADMIN_TEST_USER)


class TestToolRequestFormIntegration(ToolRequestFormIntegrationBase):
    def test_anonymous_user_cannot_submit(self):
        """Anonymous users should receive 403 (AuthenticationRequired)."""
        with self._different_user(anon=True):
            response = self._post("notifications", data=TOOL_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 403)

    def test_registered_user_can_submit(self):
        """A registered user can successfully submit a tool request via POST /api/notifications."""
        user = self._setup_user("tool_request_submitter@galaxy.test")
        with self._different_user(user["email"]):
            response = self._post("notifications", data=TOOL_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 200)
            data = response.json()
            assert "notification" in data
            assert data["notification"]["id"]

    def test_admin_receives_notification_after_submission(self):
        """After a user submits a tool request the admin should have a new notification."""
        user = self._setup_user("tool_request_sender@galaxy.test")
        with self._different_user(user["email"]):
            response = self._post("notifications", data=TOOL_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 200)

        # Admin should now have a tool_request notification
        with self._different_user(ADMIN_TEST_USER):
            notifications = self._get("notifications").json()
        tool_request_notifications = [n for n in notifications if n.get("category") == "tool_request"]
        assert (
            len(tool_request_notifications) >= 1
        ), f"Expected at least one tool_request notification for admin, got: {notifications}"

    def test_sender_receives_notification_too(self):
        """The submitter should also receive the notification in their own inbox."""
        user = self._setup_user("tool_request_sender2@galaxy.test")
        with self._different_user(user["email"]):
            self._post("notifications", data=TOOL_REQUEST_NOTIFICATION_BODY, json=True)
            notifications = self._get("notifications").json()
        tool_request_notifications = [n for n in notifications if n.get("category") == "tool_request"]
        assert (
            len(tool_request_notifications) >= 1
        ), f"Expected sender to receive the notification, got: {notifications}"

    def test_requester_email_overridden_server_side(self):
        """The requester_email in the notification content must be the user's real email, never the client-supplied one."""
        user = self._setup_user("tool_request_email_check@galaxy.test")
        payload_with_spoofed_email = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "tool_request_form",
                "category": "tool_request",
                "variant": "info",
                "content": {
                    "category": "tool_request",
                    "tool_names": ["FastQC"],
                    "tool_url": "https://github.com/s-andrews/FastQC",
                    "description": "Quality control tool for high-throughput sequencing data.",
                    "scientific_domain": "Genomics",
                    "requested_version": "0.12.1",
                    "additional_remarks": "Would be great for the genomics team.",
                    "requester_email": "spoofed@example.com",
                },
            },
        }
        with self._different_user(user["email"]):
            self._post("notifications", data=payload_with_spoofed_email, json=True)
            notifications = self._get("notifications").json()
        tool_request_notifications = [n for n in notifications if n.get("category") == "tool_request"]
        assert tool_request_notifications, "Expected at least one tool_request notification"
        content = tool_request_notifications[0]["content"]
        assert (
            content["requester_email"] == user["email"]
        ), f"requester_email should be {user['email']!r}, got {content['requester_email']!r}"

    def test_client_supplied_recipients_ignored(self):
        """The server must override recipients regardless of what the client sends."""
        user = self._setup_user("tool_request_recipients_check@galaxy.test")
        ignored_recipient = self._setup_user("tool_request_ignored_recipient@galaxy.test")
        payload_with_recipients = {
            "recipients": {"user_ids": [ignored_recipient["id"]], "group_ids": [], "role_ids": []},
            "notification": TOOL_REQUEST_NOTIFICATION_BODY["notification"],
        }
        with self._different_user(user["email"]):
            response = self._post("notifications", data=payload_with_recipients, json=True)
            # Server accepts the request and overrides recipients — should still succeed
            self._assert_status_code_is(response, 200)

        with self._different_user(ignored_recipient["email"]):
            notifications = self._get("notifications").json()
        tool_request_notifications = [n for n in notifications if n.get("category") == "tool_request"]
        assert tool_request_notifications == [], "Client-supplied recipients must be ignored for user submissions"

    def test_non_admin_cannot_send_disallowed_category(self):
        """Non-admin users may not send 'message' category notifications."""
        user = self._setup_user("tool_request_category_check@galaxy.test")
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
        user = self._setup_user("tool_request_minimal@galaxy.test")
        minimal_payload = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "tool_request_form",
                "category": "tool_request",
                "variant": "info",
                "content": {
                    "category": "tool_request",
                    "tool_names": ["Samtools"],
                    "description": "Tools for manipulating alignments in SAM format.",
                },
            },
        }
        with self._different_user(user["email"]):
            response = self._post("notifications", data=minimal_payload, json=True)
            self._assert_status_code_is(response, 200)

    def test_workflow_install_request_with_tool_names(self):
        """Submit a request that includes workflow context (multiple tool_names + workflow_id)."""
        user = self._setup_user("tool_request_workflow@galaxy.test")
        workflow_payload = {
            "recipients": {"user_ids": [], "group_ids": [], "role_ids": []},
            "notification": {
                "source": "tool_request_form",
                "category": "tool_request",
                "variant": "info",
                "content": {
                    "category": "tool_request",
                    "tool_names": [
                        "toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17",
                        "toolshed.g2.bx.psu.edu/repos/devteam/samtools/samtools/1.13",
                    ],
                    "workflow_id": "encoded-workflow-id-abc",
                    "description": "These tools are required by My Analysis workflow.",
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
            if n.get("category") == "tool_request"
            and n.get("content", {}).get("workflow_id") == "encoded-workflow-id-abc"
        ]
        assert (
            len(workflow_tool_notifications) >= 1
        ), f"Expected at least one tool_request notification with workflow_id, got: {notifications}"
        content = workflow_tool_notifications[0]["content"]
        assert content["workflow_id"] == "encoded-workflow-id-abc"
        assert len(content["tool_names"]) == 2


class TestToolRequestFormDisabledIntegration(IntegrationTestCase):
    """Tests for when the tool request form feature is disabled."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_tool_request_form"] = False
        config["enable_celery_tasks"] = False

    def test_disabled_config_returns_error(self):
        """When tool_request_form is disabled, non-admin submissions should be denied."""
        user = self._setup_user("tool_request_disabled@galaxy.test")
        with self._different_user(user["email"]):
            response = self._post("notifications", data=TOOL_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 403)

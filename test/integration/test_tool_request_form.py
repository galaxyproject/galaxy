"""Integration tests for the Tool Request Form API endpoint."""

from galaxy_test.base.api_util import ADMIN_TEST_USER
from galaxy_test.driver.integration_util import IntegrationTestCase

TOOL_REQUEST_PAYLOAD = {
    "tool_name": "FastQC",
    "tool_url": "https://github.com/s-andrews/FastQC",
    "description": "Quality control tool for high-throughput sequencing data.",
    "scientific_domain": "Genomics",
    "requested_version": "0.12.1",
    "conda_available": True,
    "test_data_available": True,
    "requester_affiliation": "Example University",
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
            response = self._post("tool_request_form", data=TOOL_REQUEST_PAYLOAD, json=True)
            self._assert_status_code_is(response, 403)

    def test_registered_user_can_submit(self):
        """A registered user can successfully submit a tool request."""
        user = self._setup_user("tool_request_submitter@galaxy.test")
        with self._different_user(user["email"]):
            response = self._post("tool_request_form", data=TOOL_REQUEST_PAYLOAD, json=True)
            # 204 No Content on success
            self._assert_status_code_is(response, 204)

    def test_admin_receives_notification_after_submission(self):
        """After a user submits a tool request the admin should have a new notification."""
        user = self._setup_user("tool_request_sender@galaxy.test")
        with self._different_user(user["email"]):
            response = self._post("tool_request_form", data=TOOL_REQUEST_PAYLOAD, json=True)
            self._assert_status_code_is(response, 204)

        # Admin should now have a tool_request notification
        with self._different_user(ADMIN_TEST_USER):
            notifications = self._get("notifications").json()
        tool_request_notifications = [n for n in notifications if n.get("category") == "tool_request"]
        assert (
            len(tool_request_notifications) >= 1
        ), f"Expected at least one tool_request notification for admin, got: {notifications}"

        sender_notifications = [
            n for n in tool_request_notifications if n["content"].get("requester_email") == user["email"]
        ]
        assert (
            len(sender_notifications) >= 1
        ), f"Expected notification from {user['email']}, got: {tool_request_notifications}"
        notification = sender_notifications[0]
        assert notification["content"]["tool_name"] == TOOL_REQUEST_PAYLOAD["tool_name"]
        assert notification["content"]["requester_name"] == user["username"]
        assert notification["content"]["requester_email"] == user["email"]
        assert notification["content"]["description"] == TOOL_REQUEST_PAYLOAD["description"]

    def test_missing_required_fields_returns_400(self):
        """Missing required fields should return 400 Bad Request."""
        user = self._setup_user("tool_request_invalid@galaxy.test")
        with self._different_user(user["email"]):
            # Missing tool_name and description (both required)
            incomplete_payload = {
                "requester_affiliation": "Example University",
            }
            response = self._post("tool_request_form", data=incomplete_payload, json=True)
            self._assert_status_code_is(response, 400)

    def test_minimal_payload_succeeds(self):
        """Only required fields (tool_name, description) should be enough to submit."""
        user = self._setup_user("tool_request_minimal@galaxy.test")
        with self._different_user(user["email"]):
            minimal_payload = {
                "tool_name": "Samtools",
                "description": "Tools for manipulating alignments in SAM format.",
            }
            response = self._post("tool_request_form", data=minimal_payload, json=True)
            self._assert_status_code_is(response, 204)

    def test_workflow_install_request_with_tool_ids(self):
        """Submit a request that includes workflow context (tool_ids + workflow_name)."""
        user = self._setup_user("tool_request_workflow@galaxy.test")
        workflow_payload = {
            "tool_name": "2 tools required by workflow My Analysis",
            "description": (
                'The following tools are required by workflow "My Analysis" '
                "but not installed: toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17, "
                "toolshed.g2.bx.psu.edu/repos/devteam/samtools/samtools/1.13."
            ),
            "tool_ids": [
                "toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17",
                "toolshed.g2.bx.psu.edu/repos/devteam/samtools/samtools/1.13",
            ],
            "workflow_name": "My Analysis",
        }
        with self._different_user(user["email"]):
            response = self._post("tool_request_form", data=workflow_payload, json=True)
            self._assert_status_code_is(response, 204)

        with self._different_user(ADMIN_TEST_USER):
            notifications = self._get("notifications").json()
        workflow_tool_notifications = [
            n
            for n in notifications
            if n.get("category") == "tool_request" and n.get("content", {}).get("workflow_name") == "My Analysis"
        ]
        assert (
            len(workflow_tool_notifications) >= 1
        ), f"Expected at least one tool_request notification with workflow_name='My Analysis', got: {notifications}"
        content = workflow_tool_notifications[0]["content"]
        assert content["workflow_name"] == "My Analysis"
        assert len(content["tool_ids"]) == 2


class TestToolRequestFormDisabledIntegration(IntegrationTestCase):
    """Tests for when the tool request form feature is disabled."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_tool_request_form"] = False
        config["enable_celery_tasks"] = False

    def test_disabled_config_returns_error(self):
        """When tool_request_form is disabled, requests should return 501."""
        user = self._setup_user("tool_request_disabled@galaxy.test")
        with self._different_user(user["email"]):
            response = self._post("tool_request_form", data=TOOL_REQUEST_PAYLOAD, json=True)
            # ServerNotConfiguredForRequest → 501 Not Implemented
            self._assert_status_code_is(response, 501)

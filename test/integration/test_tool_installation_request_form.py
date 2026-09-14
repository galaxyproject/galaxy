"""Integration tests for the tool-installation-request-form feature (routed via POST /api/notifications).

The request handler's branches (auth, category allow-list, content sanitizing,
recipient and envelope stamping) are covered by unit tests; these tests cover
what only a running server shows: the Lagom wiring, the public response shape,
real config and workflow resolution, email delivery and the rate limiter.
"""

import copy
import json
import os
import re
from typing import (
    Any,
    ClassVar,
)

from galaxy_test.base.api_util import ADMIN_TEST_USER
from galaxy_test.base.env import DEFAULT_WEB_HOST
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver.integration_util import IntegrationTestCase

TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY: dict[str, Any] = {
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
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_tool_installation_request_form"] = True
        config["enable_celery_tasks"] = False

    def setUp(self):
        super().setUp()
        # The admin user must exist in the database to be resolved as a recipient.
        self._setup_user(ADMIN_TEST_USER)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def _admin_tool_request_notifications(self) -> list[dict[str, Any]]:
        with self._different_user(ADMIN_TEST_USER):
            notifications = self._get("notifications").json()
        return [n for n in notifications if n.get("category") == "tool_installation_request"]


class TestToolInstallationRequestFormIntegration(ToolInstallationRequestFormIntegrationBase):
    def test_admin_receives_notification_after_submission(self):
        user = self._setup_user("tool_installation_request_sender@galaxy.test")
        payload = copy.deepcopy(TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY)
        # Client-supplied values for server-stamped fields must not survive.
        payload["notification"]["content"]["requester_email"] = "spoofed@example.com"
        with self._different_user(user["email"]):
            response = self._post("notifications", data=payload, json=True)
            self._assert_status_code_is(response, 200)

        notifications = self._admin_tool_request_notifications()
        # The admin inbox is shared across this class, so pick out this
        # submission by the requester email the server stamped on it.
        own = [n for n in notifications if n["content"]["requester_email"] == user["email"]]
        assert own, f"Expected a tool_installation_request notification from {user['email']}, got: {notifications}"
        assert not [n for n in notifications if n["content"]["requester_email"] == "spoofed@example.com"]
        # Server-only content (the confirmation flag, the stamped workflow name)
        # stays out of the public response.
        for notification in notifications:
            assert "is_confirmation" not in notification["content"]
            assert "workflow_name" not in notification["content"]

    def test_workflow_id_is_resolved_to_the_stored_workflow(self):
        user = self._setup_user("tool_installation_request_workflow@galaxy.test")
        with self._different_user(user["email"]):
            workflow_id = self.workflow_populator.simple_workflow("tool_installation_request_context")
        payload = copy.deepcopy(TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY)
        payload["notification"]["content"]["tools"] = [
            {"tool_shed_id": "toolshed.g2.bx.psu.edu/repos/devteam/bwa/bwa/0.7.17"},
            {"tool_shed_id": "toolshed.g2.bx.psu.edu/repos/devteam/samtools/samtools/1.13"},
        ]
        payload["notification"]["content"]["workflow_id"] = workflow_id
        with self._different_user(user["email"]):
            response = self._post("notifications", data=payload, json=True)
            self._assert_status_code_is(response, 200)

        notifications = self._admin_tool_request_notifications()
        own = [n for n in notifications if n["content"].get("workflow_id") == workflow_id]
        assert (
            own
        ), f"Expected a tool_installation_request notification for workflow {workflow_id}, got: {notifications}"
        content = own[0]["content"]
        # The name is stamped for the email at submission time but is not public.
        assert "workflow_name" not in content
        assert len(content["tools"]) == 2

    def test_workflow_id_must_name_a_workflow_accessible_to_the_submitter(self):
        # The id is linked and resolved to a workflow name in the admin-facing
        # notification, so it must not be usable to reference workflows the
        # submitter cannot see.
        owner = self._setup_user("tool_installation_request_workflow_owner@galaxy.test")
        with self._different_user(owner["email"]):
            private_workflow_id = self.workflow_populator.simple_workflow("tool_installation_request_private")
        submitter = self._setup_user("tool_installation_request_workflow_other@galaxy.test")
        payload = copy.deepcopy(TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY)
        payload["notification"]["content"]["workflow_id"] = private_workflow_id
        with self._different_user(submitter["email"]):
            response = self._post("notifications", data=payload, json=True)
            self._assert_status_code_is(response, 400)
            assert "workflow_id" in response.json()["err_msg"]


class TestToolInstallationRequestFormEmailContentIntegration(ToolInstallationRequestFormIntegrationBase):
    email_directory: ClassVar[str]

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.email_directory = cls._test_driver.mkdtemp()
        # The email channel is only registered when async (Celery) processing is on.
        config["enable_celery_tasks"] = True
        config["email_from"] = "galaxy-no-reply@example.com"
        config["smtp_server"] = f"mock_emails_to_path://{cls.email_directory}/email.json"

    def test_admin_email_is_rendered_and_sent_by_the_dispatcher(self):
        email_path = os.path.join(self.email_directory, "email.json")
        user = self._setup_user("tool_installation_request_email_delivery@galaxy.test")
        with self._different_user(user["email"]):
            # Opt the submitter out of email so the admin's is the only email produced.
            update_request = {
                "preferences": {
                    "tool_installation_request": {
                        "enabled": True,
                        "channels": {"push": True, "email": False},
                    }
                }
            }
            self._assert_status_code_is_ok(self._put("notifications/preferences", data=update_request, json=True))
            response = self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 200)
            self.dataset_populator.wait_on_task_id(response.json()["id"])

        # Emails are delivered by the periodic background dispatcher, not during the request.
        assert not os.path.exists(email_path)
        assert self._app.notification_manager.dispatch_pending_notifications_via_channels() >= 1
        with open(email_path) as f:
            email = json.load(f)
        assert email["to"] == ADMIN_TEST_USER
        assert email["subject"] == "[Galaxy] Tool installation request: FastQC"
        assert re.search(rf"^Requested by: {re.escape(user['email'])}$", email["body"], re.MULTILINE)
        assert "FastQC" in email["html"] and "Genomics" in email["html"]


class TestToolInstallationRequestFormPerHostDisabledIntegration(IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_tool_installation_request_form"] = True
        # Keyed on the host the embedded test server is reached through (a substring match).
        config["enable_tool_installation_request_form_by_host"] = {DEFAULT_WEB_HOST: False}
        config["enable_celery_tasks"] = False

    def test_per_host_disable_is_enforced_server_side(self):
        user = self._setup_user("tool_installation_request_per_host@galaxy.test")
        with self._different_user(user["email"]):
            # The client decides whether to show the form from this value, resolved per host.
            assert self._get("configuration").json()["enable_tool_installation_request_form"] is False
            response = self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
            self._assert_status_code_is(response, 403)
            # CONFIG_DOES_NOT_ALLOW, not ADMIN_REQUIRED: no amount of privilege satisfies a disabled feature.
            assert response.json()["err_code"] == 403004


class TestToolInstallationRequestFormRateLimitIntegration(ToolInstallationRequestFormIntegrationBase):
    # Own class: the limiter counts every request made against the server.
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["send_notification_rate_limit"] = "3/minute"

    def test_submissions_are_rate_limited_per_user(self):
        user = self._setup_user("tool_installation_request_rate_limit@galaxy.test")
        with self._different_user(user["email"]):
            responses = [
                self._post("notifications", data=TOOL_INSTALLATION_REQUEST_NOTIFICATION_BODY, json=True)
                for _ in range(4)
            ]
        statuses = [response.status_code for response in responses]
        assert statuses == [200, 200, 200, 429], statuses
        body = responses[-1].json()
        assert "3 per 1 minute" in body["err_msg"]
        assert body["err_code"] == 429001

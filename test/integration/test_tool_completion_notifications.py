"""Tool form notifications are delivered by the completion monitor."""

from pathlib import Path
from typing import ClassVar

import pytest

from galaxy.managers.notification import EmailNotificationChannelPlugin
from galaxy.util.unittest_utils import read_mock_emails
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    wait_on,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestToolCompletionNotifications(IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator
    email_dir: ClassVar[str]

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.email_dir = cls._test_driver.mkdtemp()
        config["email_from"] = "galaxy-noreply@example.com"
        config["smtp_server"] = f"mock_emails_to_path://{cls.email_dir}"
        config["enable_notification_system"] = True
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "extended"
        config["workflow_completion_monitor_sleep"] = 0.1

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        # Exercise the real email channel synchronously without a Celery worker.
        self._app.notification_manager.channel_plugins["email"] = EmailNotificationChannelPlugin(self._app.config)
        for email in Path(self.email_dir).iterdir():
            email.unlink()
        self._set_email_delivery(False)

    @pytest.mark.parametrize("option", ["send_notification", "send_email_notification"])
    def test_single_job_notification(self, option):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="a\n", wait=True)
            result = self.dataset_populator.run_tool(
                "cat1", {"input1": {"src": "hda", "id": hda["id"]}, option: True}, history_id
            )
            self.dataset_populator.wait_for_job(result["jobs"][0]["id"], assert_ok=True)
            [notification] = self._wait_for_notifications(history_id)
            assert "1 ok" in notification["content"]["message"]
            assert "Concatenate" in notification["content"]["subject"]
            self._app.notification_manager.dispatch_pending_notifications_via_channels()
            assert read_mock_emails(self.email_dir) == []

    def test_map_over_sends_one_summary_and_uses_the_saved_email_preference(self):
        self._set_email_delivery(True)
        with self.dataset_populator.test_history() as history_id:
            hdca = self.collection_populator.create_list_in_history(
                history_id, contents=["a\n", "b\n", "c\n"], wait=True
            ).json()["outputs"][0]
            result = self.dataset_populator.run_tool(
                "cat1",
                {"input1": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}, "send_notification": True},
                history_id,
            )
            for job in result["jobs"]:
                self.dataset_populator.wait_for_job(job["id"], assert_ok=True)
            [notification] = self._wait_for_notifications(history_id)
            assert "3 ok" in notification["content"]["message"]
            assert "Concatenate" in notification["content"]["subject"]
            self._app.notification_manager.dispatch_pending_notifications_via_channels()
            [email] = read_mock_emails(self.email_dir)
            assert email["to"] == self._get("users/current").json()["email"]
            assert "3 ok" in email["body"]
            assert f"?id={history_id}" in email["body"]

    def _set_email_delivery(self, enabled):
        response = self._put(
            "notifications/preferences",
            data={"preferences": {"tool_execution_completed": {"enabled": True, "channels": {"email": enabled}}}},
            json=True,
        )
        self._assert_status_code_is(response, 200)

    def _wait_for_notifications(self, history_id):
        def notifications():
            return [
                notification
                for notification in self._get("notifications").json()
                if notification["category"] == "tool_execution_completed"
                and f"?id={history_id}" in notification["content"]["message"]
            ] or None

        return wait_on(notifications, "tool completion notification")

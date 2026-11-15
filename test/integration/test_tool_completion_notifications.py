"""Tool form notifications are delivered by the completion monitor."""

from pathlib import Path
from typing import ClassVar

import pytest

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
        config["metadata_strategy"] = "extended"
        config["workflow_completion_monitor_sleep"] = 0.1

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
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

    @pytest.mark.parametrize("asynchronous", [False, True])
    def test_map_over_sends_one_summary_and_uses_the_saved_email_preference(self, asynchronous):
        self._set_email_delivery(True)
        with self.dataset_populator.test_history() as history_id:
            hdca = self.collection_populator.create_list_in_history(
                history_id, contents=["a\n", "b\n", "c\n"], wait=True
            ).json()["outputs"][0]
            batch = {"__class__": "Batch"} if asynchronous else {"batch": True}
            inputs = {"input1": {**batch, "values": [{"src": "hdca", "id": hdca["id"]}]}}
            if asynchronous:
                response = self.dataset_populator.tool_request_raw(
                    "cat1", inputs, history_id, strict=False, send_notification=True
                )
                self._assert_status_code_is(response, 200)
                request_id = response.json()["tool_request_id"]
                assert self.dataset_populator.wait_on_tool_request(request_id)
                jobs = self.galaxy_interactor.jobs_for_tool_request(request_id)
            else:
                jobs = self.dataset_populator.run_tool("cat1", {**inputs, "send_notification": True}, history_id)[
                    "jobs"
                ]
            self.dataset_populator.wait_for_jobs(jobs, assert_ok=True)
            [notification] = self._wait_for_notifications(history_id)
            assert "3 ok" in notification["content"]["message"]
            assert "Concatenate" in notification["content"]["subject"]
            [email] = wait_on(
                lambda: [email for email in read_mock_emails(self.email_dir) if f"?id={history_id}" in email["body"]]
                or None,
                "completion email",
            )
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

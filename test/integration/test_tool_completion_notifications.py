"""Tool form notifications are delivered by the completion monitor."""

import pytest

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    wait_on,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestToolCompletionNotifications(IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "extended"
        config["workflow_completion_monitor_sleep"] = 0.1

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

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

    def test_map_over_sends_one_summary(self):
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

    def _wait_for_notifications(self, history_id):
        def notifications():
            return [
                notification
                for notification in self._get("notifications").json()
                if notification["category"] == "tool_execution_completed"
                and f"?id={history_id}" in notification["content"]["message"]
            ] or None

        return wait_on(notifications, "tool completion notification")

"""Tool form notifications are delivered by the completion monitor."""

from pathlib import Path
from typing import ClassVar

import pytest

from galaxy.util.unittest_utils import read_mock_emails
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    wait_on,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
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
        config["enable_quotas"] = True
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
            assert notification["content"]["job_id"] == result["jobs"][0]["id"]
            assert notification["content"]["implicit_collection_jobs_id"] is None
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
            assert notification["content"]["job_id"] is None
            group_id = notification["content"]["implicit_collection_jobs_id"]
            assert group_id
            source_jobs = self._get("jobs", data={"implicit_collection_jobs_id": group_id})
            self._assert_status_code_is(source_jobs, 200)
            assert {job["id"] for job in source_jobs.json()} == {job["id"] for job in jobs}
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

    @pytest.mark.parametrize("workflow", [False, True])
    def test_quota_pause_then_resume_sends_attention_and_completion(self, workflow):
        with self.dataset_populator.test_history() as history_id:
            hdca = self.collection_populator.create_list_in_history(
                history_id, contents=["first dataset\n", "second dataset\n"], wait=True
            ).json()["outputs"][0]
            quota = self.dataset_populator.create_quota(
                {
                    "name": f"pause-notifications-{history_id}",
                    "description": "Pause this user's jobs until the quota is removed",
                    "amount": "1 bytes",
                    "operation": "=",
                    "default": "no",
                    "in_users": [self._get("users/current").json()["email"]],
                    "in_groups": [],
                }
            )
            try:
                if workflow:
                    workflows = WorkflowPopulator(self.galaxy_interactor)
                    workflow_id = workflows.upload_yaml_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
                    response = workflows.invoke_workflow(
                        workflow_id,
                        history_id=history_id,
                        inputs={"input1": {"src": "hdca", "id": hdca["id"]}},
                        inputs_by="name",
                        request={"on_complete": [{"send_notification": {}}]},
                    )
                    response.raise_for_status()
                    invocation_id = response.json()["id"]
                    link = f"/workflows/invocations/{invocation_id}"
                else:
                    self.dataset_populator.run_tool(
                        "cat1",
                        {
                            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]},
                            "send_notification": True,
                        },
                        history_id,
                    )
                    link = f"?id={history_id}"

                def run_notifications():
                    return [
                        notification
                        for notification in self._get("notifications").json()
                        if link in notification["content"].get("message", "")
                    ]

                [attention] = wait_on(lambda: run_notifications() or None, "paused run notification")
                assert attention["content"]["event"] == "needs_attention"
                paused_jobs = wait_on(
                    lambda: [
                        job
                        for job in self._get("jobs", data={"history_id": history_id}).json()
                        if job["state"] == "paused"
                    ]
                    or None,
                    "quota-paused jobs",
                )
            finally:
                self._delete(f"quotas/{quota['id']}", data={"purge": "true"}, admin=True, json=True).raise_for_status()
            for job in paused_jobs:
                self._put(f"jobs/{job['id']}/resume").raise_for_status()
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            notifications = wait_on(
                lambda: (items if len(items := run_notifications()) == 2 else None),
                "resumed run completion notification",
            )
            assert sorted(n["content"]["event"] for n in notifications) == ["completed", "needs_attention"]
            completed = next(n for n in notifications if n["content"]["event"] == "completed")
            assert ("ok: 2" if workflow else "2 ok") in completed["content"]["message"]

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


class TestSmtpOnlyCompletionEmails(IntegrationTestCase):
    """Completion emails work with the notification system and Celery disabled."""

    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    email_dir: ClassVar[str]

    # Override the integration harness's default Celery fixtures: no worker or broker.
    @pytest.fixture(autouse=True, scope="session")
    def _request_celery_app(self):
        pass

    @pytest.fixture(autouse=True, scope="session")
    def _request_celery_worker(self):
        pass

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.email_dir = cls._test_driver.mkdtemp()
        config.update(
            enable_notification_system=False,
            enable_celery_tasks=False,
            metadata_strategy="extended",
            smtp_server=f"mock_emails_to_path://{cls.email_dir}",
            email_from="galaxy-noreply@example.com",
            workflow_completion_monitor_sleep=0.1,
        )

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @pytest.mark.parametrize("option", ["send_notification", "send_email_notification"])
    def test_map_over_sends_one_email_without_notifications_or_celery(self, option):
        with self.dataset_populator.test_history() as history_id:
            hdca = (
                DatasetCollectionPopulator(self.galaxy_interactor)
                .create_list_in_history(history_id, contents=["a\n", "b\n", "c\n"], wait=True)
                .json()["outputs"][0]
            )
            jobs = self.dataset_populator.run_tool(
                "cat1",
                {"input1": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}, option: True},
                history_id,
            )["jobs"]
            self.dataset_populator.wait_for_jobs(jobs, assert_ok=True)
            email = self._wait_for_email(f"?id={history_id}")
            assert "3 ok" in email["body"]

    def test_workflow_email_without_celery(self):
        with self.dataset_populator.test_history() as history_id:
            workflows = WorkflowPopulator(self.galaxy_interactor)
            summary = workflows.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
                extra_invocation_kwds={"on_complete": [{"send_notification": {}}]},
            )
            workflows.wait_for_invocation_and_completion(summary.invocation_id)
            email = self._wait_for_email(f"/workflows/invocations/{summary.invocation_id}")
            assert "ok: 1" in email["body"]

    def _wait_for_email(self, link):
        [email] = wait_on(
            lambda: [email for email in read_mock_emails(self.email_dir) if link in email["body"]] or None,
            "SMTP-only completion email",
        )
        assert email["to"] == self._get("users/current").json()["email"]
        assert "/user/notifications" not in email["body"]
        # SMTP fallback must not enable the rest of the notification system.
        self._assert_status_code_is(self._get("notifications/preferences"), 403)
        return email

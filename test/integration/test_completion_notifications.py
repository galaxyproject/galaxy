"""Job completion emails and notifications requested with the tool form's email notification option."""

from pathlib import Path
from typing import ClassVar

from galaxy.util.unittest_utils import read_mock_emails
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    wait_on,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from galaxy_test.driver import integration_util

# One worker finishes the jobs of a map-over one after the other, so the last job always sees the
# others settled and no two jobs can both send the summary.
SINGLE_WORKER_JOB_CONFIG = {
    "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
    "execution": {"default": "local", "environments": {"local": {"runner": "local"}}},
}


def run_cat1_notifying(dataset_populator: DatasetPopulator, history_id: str, input1: dict) -> dict:
    """Run cat1 with the tool form's email notification option and wait for its jobs."""
    response = dataset_populator.run_tool("cat1", {"input1": input1, "send_email_notification": True}, history_id)
    for job in response["jobs"]:
        dataset_populator.wait_for_job(job["id"], assert_ok=True)
    return response


class TestJobCompletionEmails(integration_util.IntegrationTestCase):
    email_dir: ClassVar[str]
    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.email_dir = cls._test_driver.mkdtemp()
        config["email_from"] = "galaxy-noreply@example.com"
        config["smtp_server"] = f"mock_emails_to_path://{cls.email_dir}"
        config["job_config"] = SINGLE_WORKER_JOB_CONFIG

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        for email in Path(self.email_dir).iterdir():
            email.unlink()

    def test_job_sends_its_own_email(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="a\n", wait=True)

            run_cat1_notifying(self.dataset_populator, history_id, {"src": "hda", "id": hda["id"]})

            [email] = self._wait_for_emails()
            assert email["to"] == self._current_user_email()
            assert email["body"].startswith("Your Galaxy job generating dataset(s):")

    def test_map_over_sends_one_summary_email(self):
        with self.dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\n", "b\n", "c\n"], wait=True
            ).json()["outputs"][0]

            run_cat1_notifying(
                self.dataset_populator, history_id, {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}
            )

            [email] = self._wait_for_emails()
            assert email["to"] == self._current_user_email()
            assert email["body"].startswith("Your 3 Galaxy jobs generating collection(s):")
            assert "are complete (3 ok) as of " in email["body"]

    def _wait_for_emails(self) -> list[dict]:
        # Emails are sent right after the commit that finishes a job, so they may lag its state.
        return wait_on(lambda: read_mock_emails(self.email_dir) or None, "job completion email")

    def _current_user_email(self) -> str:
        return self._get("users/current").json()["email"]


class TestCompletionNotifications(integration_util.IntegrationTestCase):
    """With the notification system and Celery on, completion goes through the notification system."""

    email_dir: ClassVar[str]
    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator
    workflow_populator: WorkflowPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_notification_system"] = True
        config["enable_celery_tasks"] = True
        config["job_config"] = SINGLE_WORKER_JOB_CONFIG
        cls.email_dir = cls._test_driver.mkdtemp()
        config["email_from"] = "galaxy-noreply@example.com"
        config["smtp_server"] = f"mock_emails_to_path://{cls.email_dir}"
        # Far beyond a test's duration: completion emails must not wait for the pending notifications dispatcher.
        config["dispatch_notifications_interval"] = 3600

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        for email in Path(self.email_dir).iterdir():
            email.unlink()

    def test_job_sends_its_own_notification(self):
        with self.dataset_populator.test_history(name="Reads") as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="a\n", wait=True)

            response = run_cat1_notifying(self.dataset_populator, history_id, {"src": "hda", "id": hda["id"]})

            [notification] = self._wait_for_notifications(history_id)
            assert notification["content"] == {
                "category": "job_completion",
                "history_id": history_id,
                "history_name": "Reads",
                "outputs": [response["outputs"][0]["name"]],
                "job_count": 1,
                "state_counts": {"ok": 1},
                "invocation_id": None,
            }
            assert self._wait_for_email_subjects() == ["[Galaxy] Job completion notification from history 'Reads'"]

    def test_map_over_sends_one_notification(self):
        with self.dataset_populator.test_history(name="Reads") as history_id:
            hdca = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\n", "b\n", "c\n"], wait=True
            ).json()["outputs"][0]

            response = run_cat1_notifying(
                self.dataset_populator, history_id, {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}
            )

            [notification] = self._wait_for_notifications(history_id)
            assert notification["category"] == "job_completion"
            assert notification["variant"] == "info"
            assert notification["content"] == {
                "category": "job_completion",
                "history_id": history_id,
                "history_name": "Reads",
                "outputs": [response["implicit_collections"][0]["name"]],
                "job_count": 3,
                "state_counts": {"ok": 3},
                "invocation_id": None,
            }
            assert self._wait_for_email_subjects() == ["[Galaxy] Job completion notification from history 'Reads'"]

    def test_workflow_invocation_sends_one_notification(self):
        with self.dataset_populator.test_history(name="Reads") as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                assert_ok=True,
                extra_invocation_kwds={"on_complete": [{"send_notification": {}}]},
            )
            self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id)

            workflow_name = self._get(f"workflows/{summary.workflow_id}").json()["name"]
            [notification] = self._wait_for_notifications(history_id)
            assert notification["category"] == "workflow_completion"
            assert notification["content"] == {
                "category": "workflow_completion",
                "history_id": history_id,
                "history_name": "Reads",
                "workflow_name": workflow_name,
                "job_count": 1,
                "state_counts": {"ok": 1},
                "invocation_id": summary.invocation_id,
            }
            assert self._wait_for_email_subjects() == [f"[Galaxy] Workflow '{workflow_name}' completed"]

    def _wait_for_notifications(self, history_id: str) -> list[dict]:
        """The notifications about jobs in the history; Celery tasks create them once the jobs complete."""

        def history_notifications():
            notifications = self._get("notifications").json()
            return [n for n in notifications if n["content"].get("history_id") == history_id] or None

        return wait_on(history_notifications, "job completion notification")

    def _wait_for_email_subjects(self) -> list[str]:
        """The subjects of the emails sent; the Celery task sends them right after creating the notification."""
        return wait_on(
            lambda: [email["subject"] for email in read_mock_emails(self.email_dir)] or None, "completion email"
        )

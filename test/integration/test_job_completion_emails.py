"""Job completion emails requested with the tool form's email notification option."""

from pathlib import Path
from typing import ClassVar

from galaxy.util.unittest_utils import read_mock_emails
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    wait_on,
)
from galaxy_test.driver import integration_util

# One worker finishes the jobs of a map-over one after the other, so the last job always sees the
# others settled and no two jobs can both send the summary.
SINGLE_WORKER_JOB_CONFIG = {
    "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 1}},
    "execution": {"default": "local", "environments": {"local": {"runner": "local"}}},
}


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

            self._run_cat1_with_email(history_id, {"src": "hda", "id": hda["id"]})

            [email] = self._wait_for_emails()
            assert email["to"] == self._current_user_email()
            assert email["body"].startswith("Your Galaxy job generating dataset(s):")

    def test_map_over_sends_one_summary_email(self):
        with self.dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\n", "b\n", "c\n"], wait=True
            ).json()["outputs"][0]

            self._run_cat1_with_email(history_id, {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]})

            [email] = self._wait_for_emails()
            assert email["to"] == self._current_user_email()
            assert email["body"].startswith("Your 3 Galaxy jobs generating collection(s):")
            assert "are complete (3 ok) as of " in email["body"]

    def _run_cat1_with_email(self, history_id: str, input1: dict) -> None:
        response = self.dataset_populator.run_tool(
            "cat1", {"input1": input1, "send_email_notification": True}, history_id
        )
        for job in response["jobs"]:
            self.dataset_populator.wait_for_job(job["id"], assert_ok=True)

    def _wait_for_emails(self) -> list[dict]:
        # Emails are sent right after the commit that finishes a job, so they may lag its state.
        return wait_on(lambda: read_mock_emails(self.email_dir) or None, "job completion email")

    def _current_user_email(self) -> str:
        return self._get("users/current").json()["email"]

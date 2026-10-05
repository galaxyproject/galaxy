"""Integration tests running jobs on Crypt4GH-encrypted datasets against a mock recryptor service."""

import io
from datetime import timedelta
from typing import Any

from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model import Job
from galaxy_test.base.crypt4gh import (
    encrypt,
    generate_keypair,
    Keypair,
    MockRecryptorService,
)
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

PLAINTEXT_1 = b"@read1\nACGT\n+\nIIII\n"
PLAINTEXT_2 = b"@read2\nTTTT\n+\nIIII\n"


class BaseCrypt4GHExecutionIntegrationTestCase(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    service: MockRecryptorService

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.service = MockRecryptorService().start()
        config["crypt4gh_enabled"] = True
        config["crypt4gh_recryptor_url"] = cls.service.url
        config["metadata_strategy"] = "extended"
        config["outputs_to_working_directory"] = True
        config["retry_metadata_internally"] = False

    @classmethod
    def tearDownClass(cls):
        cls.service.stop()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.service.requests.clear()
        self.service.failures.clear()
        self.user = generate_keypair()

    def _upload_encrypted(self, history_id: str, plaintext: bytes, user: Keypair | None = None) -> tuple[dict, bytes]:
        encrypted = encrypt(plaintext, (user or self.user).public)
        dataset = self.dataset_populator.new_dataset(
            history_id,
            content=io.BytesIO(encrypted),
            name="reads.fastqsanger.c4gh",
            file_type="auto",
            wait=True,
        )
        assert dataset["extension"] == "fastqsanger.c4gh"
        return dataset, encrypted

    def _authorize(self, dataset_id: str, encrypted: bytes, expires_in: timedelta = timedelta(days=7)) -> None:
        """Do what the browser does with the user-side recryptor service."""
        key_ref = self.service.get_compute_key_info(self.user.public, expires_in=expires_in)
        recrypted = self.service.user_recrypt(encrypted, self.user, key_ref)
        payload = {
            "scheme": "crypt4gh",
            "crypt4gh_compute_header": recrypted["crypt4gh_header"],
            "crypt4gh_compute_keypair_id": recrypted["crypt4gh_compute_keypair_id"],
            "crypt4gh_compute_keypair_expiration_date": recrypted["crypt4gh_compute_keypair_expiration_date"],
        }
        response = self._put(f"datasets/{dataset_id}/protection", payload, json=True)
        self._assert_status_code_is(response, 200)

    def _upload_authorized(self, history_id: str, plaintext: bytes) -> dict:
        dataset, encrypted = self._upload_encrypted(history_id, plaintext)
        self._authorize(dataset["id"], encrypted)
        return dataset

    def _run_cat(self, history_id: str, input1: dict, *others: dict):
        inputs: dict[str, Any] = {"input1": {"src": "hda", "id": input1["id"]}}
        for i, other in enumerate(others):
            inputs[f"queries_{i}|input2"] = {"src": "hda", "id": other["id"]}
        return self.dataset_populator.run_tool_raw("cat", inputs, history_id)

    def _wait_for_job(self, history_id: str, response) -> tuple[dict, dict]:
        self._assert_status_code_is(response, 200)
        job_id = response.json()["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id, assert_ok=False)
        job = self.dataset_populator.get_job_details(job_id, full=True).json()
        output = self.dataset_populator.get_history_dataset_details(
            history_id=history_id, content_id=response.json()["outputs"][0]["id"], assert_ok=False
        )
        return job, output

    def _job_directory_exists(self, encoded_job_id: str) -> bool:
        job = self._app.model.session.get(Job, self._app.security.decode_id(encoded_job_id))
        assert job
        return JobWorkingDirectory(job, self._app.object_store).exists()


class TestCrypt4GHExecutionIntegration(BaseCrypt4GHExecutionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # Protected jobs must remove their working directory anyway.
        config["cleanup_job"] = "never"
        # Outputs are encrypted once a job ran, the compute key must outlive the longest possible job.
        config["job_config"] = {
            "runners": {"local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 2}},
            "execution": {"default": "local", "environments": {"local": {"runner": "local"}}},
            "limits": [{"type": "walltime", "value": "48:00:00"}],
        }

    def test_authorized_job_reads_decrypted_inputs(self, history_id):
        encrypted_1 = self._upload_authorized(history_id, PLAINTEXT_1)
        encrypted_2 = self._upload_authorized(history_id, PLAINTEXT_2)
        plain = self.dataset_populator.new_dataset(history_id, content="plain\n", file_type="txt", wait=True)

        job, output = self._wait_for_job(history_id, self._run_cat(history_id, encrypted_1, encrypted_2, plain))

        assert job["state"] == "ok", job
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output, type="bytes")
        assert content == PLAINTEXT_1 + PLAINTEXT_2 + b"plain\n"
        assert self.service.routes_called() == ["recrypt_header_to_job_key"] * 2
        # Protected jobs never keep their working directory, whatever cleanup_job says.
        assert not self._job_directory_exists(job["id"])

    def test_unauthorized_input_is_refused_before_any_service_call(self, history_id):
        dataset, _ = self._upload_encrypted(history_id, PLAINTEXT_1)
        response = self._run_cat(history_id, dataset)
        self._assert_status_code_is(response, 400)
        assert "not authorized to decrypt" in response.json()["err_msg"]
        assert self.service.requests == []

    def test_shared_copy_is_refused_before_any_service_call(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        self.dataset_populator.make_public(history_id)
        with self._different_user("crypt4gh_recipient@bx.psu.edu"):
            recipient_history_id = self.dataset_populator.new_history()
            copy = self._post(
                f"histories/{recipient_history_id}/contents",
                {"source": "hda", "content": dataset["id"], "type": "dataset"},
                json=True,
            ).json()
            # Running on the shared dataset directly or on a copy is refused alike.
            for target in (dataset, copy):
                response = self._run_cat(recipient_history_id, target)
                self._assert_status_code_is(response, 400)
        assert self.service.requests == []

    def test_grant_expiring_during_the_job_is_refused_when_preparing(self, history_id):
        dataset, encrypted = self._upload_encrypted(history_id, PLAINTEXT_1)
        # Usable right now, but expires before a job hitting the 48h walltime would be done.
        self._authorize(dataset["id"], encrypted, expires_in=timedelta(hours=30))

        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))

        assert job["state"] == "error"
        assert "Authorize the dataset again" in output["misc_info"]
        assert self.service.requests == []

    def test_failed_decryption_fails_the_job_before_the_tool_runs(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        self.service.failures["recrypt_header_to_job_key"] = [422]

        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))

        assert job["state"] == "error"
        assert "Job setup failed: Could not decrypt the protected inputs" in output["misc_info"]
        assert "could not open the header" in output["misc_info"]
        assert self.service.routes_called() == ["recrypt_header_to_job_key"]

    def test_explicitly_encrypted_inputs_are_not_decrypted(self, history_id):
        # No authorization needed, the tool reads the encrypted file.
        dataset, _ = self._upload_encrypted(history_id, PLAINTEXT_1)
        response = self.dataset_populator.run_tool_raw(
            "crypt4gh_encrypted_input", {"input1": {"src": "hda", "id": dataset["id"]}}, history_id
        )
        job, output = self._wait_for_job(history_id, response)
        assert job["state"] == "ok", job
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
        assert content == "crypt4gh"
        assert self.service.requests == []
        # Not a protected job, regular cleanup rules apply.
        assert self._job_directory_exists(job["id"])


class TestCrypt4GHRemoteToolEvaluationIntegration(BaseCrypt4GHExecutionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["tool_evaluation_strategy"] = "remote"

    def test_authorized_job_reads_decrypted_inputs(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))
        assert job["state"] == "ok", job
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output, type="bytes")
        assert content == PLAINTEXT_1


class TestCrypt4GHUnsafeDestinationIntegration(BaseCrypt4GHExecutionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["outputs_to_working_directory"] = False

    def test_destination_that_cannot_protect_outputs_is_refused(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))
        assert job["state"] == "error"
        assert "outputs_to_working_directory must be enabled" in output["misc_info"]
        assert self.service.requests == []

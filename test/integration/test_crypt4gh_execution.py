"""Integration tests running jobs on Crypt4GH-encrypted datasets against a mock recryptor service."""

import io
from datetime import timedelta
from typing import Any

from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model import Job
from galaxy_test.base.crypt4gh import (
    decrypt,
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
        config["metadata_strategy"] = "extended"
        config["outputs_to_working_directory"] = True
        config["retry_metadata_internally"] = False
        config["job_config"] = cls._job_config()

    @classmethod
    def _job_config(cls, limits: list[dict[str, Any]] | None = None, **environment: Any) -> dict[str, Any]:
        """A local destination set up for protected jobs."""
        return {
            "runners": {
                "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner", "workers": 2},
                # Used when splitting jobs into tasks (use_tasked_jobs).
                "tasks": {"load": "galaxy.jobs.runners.tasks:TaskedJobRunner"},
            },
            "execution": {
                "default": "local",
                "environments": {
                    "local": {"runner": "local", "crypt4gh_recryptor_url": cls.service.url, **environment}
                },
            },
            "limits": limits or [],
        }

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

    def _authorize(
        self,
        dataset_id: str,
        encrypted: bytes,
        expires_in: timedelta = timedelta(days=7),
        user: Keypair | None = None,
    ) -> None:
        """Do what the browser does with the user-side recryptor service."""
        user = user or self.user
        key_ref = self.service.get_compute_key_info(user.public, expires_in=expires_in)
        recrypted = self.service.user_recrypt(encrypted, user, key_ref)
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

    def _decrypted_content(self, history_id: str, dataset: dict, filename: str | None = None) -> bytes:
        """Download a dataset and decrypt it with the user's key, failing if it isn't encrypted for them."""
        content = self.dataset_populator.get_history_dataset_content(
            history_id, dataset_id=dataset["id"], filename=filename, type="bytes"
        )
        assert content.startswith(b"crypt4gh"), f"{dataset['name']} is not encrypted"
        return decrypt(content, self.user.secret)

    def _ready(self, dataset_id: str) -> bool:
        return self._get(f"datasets/{dataset_id}/protection").json()["ready"]

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
        config["job_config"] = cls._job_config(limits=[{"type": "walltime", "value": "48:00:00"}])

    def test_authorized_job_outputs_are_encrypted_for_the_user(self, history_id):
        encrypted_1 = self._upload_authorized(history_id, PLAINTEXT_1)
        encrypted_2 = self._upload_authorized(history_id, PLAINTEXT_2)
        plain = self.dataset_populator.new_dataset(history_id, content="plain\n", file_type="txt", wait=True)

        job, output = self._wait_for_job(history_id, self._run_cat(history_id, encrypted_1, encrypted_2, plain))

        assert job["state"] == "ok", job
        assert output["extension"] == "fastqsanger.c4gh"
        assert self._decrypted_content(history_id, output) == PLAINTEXT_1 + PLAINTEXT_2 + b"plain\n"
        assert self.service.routes_called() == ["recrypt_header_to_job_key"] * 2 + ["recrypt_header_to_user_key"]
        # The user can use the output in further jobs right away.
        assert self._ready(output["id"])
        # Protected jobs never keep their working directory, whatever cleanup_job says.
        assert not self._job_directory_exists(job["id"])

    def test_every_kind_of_output_is_encrypted(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        response = self.dataset_populator.run_tool_raw(
            "crypt4gh_output_kinds", {"input1": {"src": "hda", "id": dataset["id"]}}, history_id
        )
        job, _ = self._wait_for_job(history_id, response)
        assert job["state"] == "ok", job

        results: dict[str, Any] = {}
        for output_name, output in job["outputs"].items():
            details = self.dataset_populator.get_history_dataset_details(
                history_id, content_id=output["id"], assert_ok=False
            )
            try:
                content: Any = self._decrypted_content(history_id, details)
            except Exception as e:
                content = f"not decryptable: {e}"
            results[output_name] = (details["state"], details["extension"], self._ready(output["id"]), content)

        protected_outputs = {
            "declared": PLAINTEXT_1,
            # Linked to the decrypted input.
            "linked": PLAINTEXT_1,
            "work_dir": PLAINTEXT_1,
            "assigned": PLAINTEXT_1,
            # Outputs only used to discover others are empty.
            "discovered": b"",
            "__new_primary_file_discovered|disc1__": PLAINTEXT_1,
            "__new_primary_file_discovered|disc2__": PLAINTEXT_1,
            "reports": b"",
            "__new_primary_file_reports|with_metadata__": PLAINTEXT_1,
            "composite": b"<html/>\n",
            "__new_primary_file_split|element1__": PLAINTEXT_1,
            "__new_primary_file_split|element2__": PLAINTEXT_1,
        }
        for output_name, expected_content in protected_outputs.items():
            state, extension, ready, content = results.pop(output_name)
            assert (state, extension.endswith("c4gh"), ready, content) == ("ok", True, True, expected_content), (
                output_name,
                results,
            )
        assert not results, f"unexpected outputs {results}"

        with_metadata = self.dataset_populator.get_history_dataset_details(
            history_id, content_id=job["outputs"]["__new_primary_file_reports|with_metadata__"]["id"]
        )
        # Tool provided metadata may come from decrypted data, it is ignored.
        assert with_metadata["extension"] == "tabular.c4gh"
        assert with_metadata.get("metadata_columns") != 99
        composite = self.dataset_populator.get_history_dataset_details(
            history_id, content_id=job["outputs"]["composite"]["id"]
        )
        assert self._decrypted_content(history_id, composite, filename="part.txt") == PLAINTEXT_1

    def test_outputs_can_be_used_in_further_jobs(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        first = self._run_cat(history_id, dataset)
        self._assert_status_code_is(first, 200)
        # Requested before the first job finished, like a workflow step: its input isn't ready (nor
        # authorized) yet, the job has to wait for the grant recorded when the first job finishes.
        second = self._run_cat(history_id, first.json()["outputs"][0])
        job, second_output = self._wait_for_job(history_id, second)
        assert job["state"] == "ok", job
        assert self._decrypted_content(history_id, second_output) == PLAINTEXT_1

    def test_own_jobs_decrypting_inputs_are_reused(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        first, _ = self._wait_for_job(history_id, self._run_cat(history_id, dataset))
        assert first["state"] == "ok", first

        response = self.dataset_populator.run_tool_raw(
            "cat", {"input1": {"src": "hda", "id": dataset["id"]}}, history_id, use_cached_job=True
        )
        second, output = self._wait_for_job(history_id, response)

        assert second["state"] == "ok", second
        assert second["copied_from_job_id"] == first["id"]
        assert self._decrypted_content(history_id, output) == PLAINTEXT_1
        assert self.service.routes_called().count("recrypt_header_to_job_key") == 1

    def test_other_users_jobs_decrypting_inputs_are_not_reused(self, history_id):
        recipient = generate_keypair()
        encrypted = encrypt(PLAINTEXT_1, self.user.public, recipient.public)
        dataset = self.dataset_populator.new_dataset(
            history_id, content=io.BytesIO(encrypted), name="reads.fastqsanger.c4gh", file_type="auto", wait=True
        )
        self._authorize(dataset["id"], encrypted)
        first, _ = self._wait_for_job(history_id, self._run_cat(history_id, dataset))
        assert first["state"] == "ok", first
        self.dataset_populator.make_public(history_id)

        with self._different_user("crypt4gh_cache_recipient@bx.psu.edu"):
            # The file is encrypted for the recipient too, who authorizes it with their own key.
            self._authorize(dataset["id"], encrypted, user=recipient)
            recipient_history_id = self.dataset_populator.new_history()
            response = self.dataset_populator.run_tool_raw(
                "cat", {"input1": {"src": "hda", "id": dataset["id"]}}, recipient_history_id, use_cached_job=True
            )
            second, output = self._wait_for_job(recipient_history_id, response)
            content = self.dataset_populator.get_history_dataset_content(
                recipient_history_id, dataset_id=output["id"], type="bytes"
            )

        assert second["state"] == "ok", second
        assert second.get("copied_from_job_id") is None
        # Outputs reused from the first job would be encrypted for its user only.
        assert decrypt(content, recipient.secret) == PLAINTEXT_1

    def test_outputs_failing_to_be_encrypted_are_purged(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        self.service.failures["recrypt_header_to_user_key"] = [422]

        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))

        assert job["state"] == "error"
        assert output["purged"], output
        assert "could not be protected" in output["misc_info"], output["misc_info"]
        assert self.service.routes_called()[-1] == "recrypt_header_to_user_key"

    def test_tool_output_is_kept_out_of_dataset_info(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        response = self.dataset_populator.run_tool_raw(
            "crypt4gh_echo_input", {"input1": {"src": "hda", "id": dataset["id"]}}, history_id
        )
        job, output = self._wait_for_job(history_id, response)
        assert job["state"] == "ok", job
        assert "ACGT" not in (output["misc_info"] or "")
        assert self._decrypted_content(history_id, output) == PLAINTEXT_1

    def test_unauthorized_input_is_refused_before_any_service_call(self, history_id):
        dataset, _ = self._upload_encrypted(history_id, PLAINTEXT_1)
        response = self._run_cat(history_id, dataset)
        self._assert_status_code_is(response, 400)
        assert "not authorized to decrypt" in response.json()["err_msg"]
        assert self.service.requests == []

    def test_unauthorized_input_is_refused_through_tool_requests(self, history_id):
        # The tool form submits through tool requests, which create jobs asynchronously.
        dataset, _ = self._upload_encrypted(history_id, PLAINTEXT_1)
        response = self.dataset_populator.tool_request_raw(
            "cat", {"input1": {"src": "hda", "id": dataset["id"]}}, history_id
        )
        self._assert_status_code_is(response, 200)
        tool_request_id = response.json()["tool_request_id"]
        assert not self.dataset_populator.wait_on_tool_request(tool_request_id)
        tool_request = self.dataset_populator.get_tool_request(tool_request_id)
        assert tool_request["state"] == "failed", tool_request
        assert "not authorized to decrypt" in tool_request["state_message"]["err_msg"]
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

    def test_authorized_job_outputs_are_encrypted_for_the_user(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))
        assert job["state"] == "ok", job
        assert self._decrypted_content(history_id, output) == PLAINTEXT_1


class TestCrypt4GHUnsafeDestinationIntegration(BaseCrypt4GHExecutionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["outputs_to_working_directory"] = False

    def test_destination_that_cannot_protect_outputs_is_refused(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))
        assert job["state"] == "error"
        assert "tools must write outputs into the job directory" in output["misc_info"]
        assert self.service.requests == []


class TestCrypt4GHExternalMetadataDestinationIntegration(BaseCrypt4GHExecutionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # Metadata, and so output encryption, would run on the Galaxy server after the job.
        config["job_config"] = cls._job_config(embed_metadata_in_job=False)

    def test_destination_collecting_metadata_after_the_job_is_refused(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))
        assert job["state"] == "error"
        assert "metadata must be collected within the job" in output["misc_info"]
        assert self.service.requests == []


class TestCrypt4GHMetadataRetryIntegration(BaseCrypt4GHExecutionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # Galaxy's default: failed metadata is collected again on the Galaxy server.
        config["retry_metadata_internally"] = True

    def test_outputs_failing_to_be_encrypted_are_purged(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        self.service.failures["recrypt_header_to_user_key"] = [422]

        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))

        assert job["state"] == "error"
        assert output["purged"], output
        response = self._get(f"datasets/{output['id']}/display")
        assert PLAINTEXT_1.decode() not in response.text


class TestCrypt4GHJobLimitsIntegration(BaseCrypt4GHExecutionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config"] = cls._job_config(limits=[{"type": "output_size", "value": "10"}])

    def test_outputs_of_jobs_failed_while_running_are_not_stored(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        response = self.dataset_populator.run_tool_raw(
            "crypt4gh_write_and_wait", {"input1": {"src": "hda", "id": dataset["id"]}}, history_id
        )

        job, output = self._wait_for_job(history_id, response)

        assert job["state"] == "error"
        assert "grew too large" in output["misc_info"]
        response = self._get(f"datasets/{output['id']}/display")
        assert PLAINTEXT_1.decode() not in response.text


class TestCrypt4GHTaskSplittingIntegration(BaseCrypt4GHExecutionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["use_tasked_jobs"] = True

    def test_jobs_that_would_be_split_into_tasks_are_refused(self, history_id):
        dataset = self._upload_authorized(history_id, PLAINTEXT_1)
        response = self.dataset_populator.run_tool_raw(
            "parallelism", {"input1": {"src": "hda", "id": dataset["id"]}}, history_id
        )
        job, output = self._wait_for_job(history_id, response)
        assert job["state"] == "error"
        assert "jobs can't be split into tasks" in output["misc_info"]
        assert self.service.requests == []

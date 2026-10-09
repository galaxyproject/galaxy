"""Run jobs on Crypt4GH-encrypted datasets through an embedded Pulsar with remote extended metadata."""

import os
from typing import Any

import pytest

from galaxy.util import safe_makedirs
from . import test_crypt4gh_execution

AMQP_URL = os.environ.get("GALAXY_TEST_AMQP_URL")


def _pulsar_job_config(recryptor_url: str, environment: dict[str, Any], runner: dict[str, Any]) -> dict[str, Any]:
    return {
        "runners": {
            "local": {"load": "galaxy.jobs.runners.local:LocalJobRunner"},
            # Not named after Pulsar: Galaxy must recognize Pulsar runners by their class.
            "remote": {
                **runner,
                "pulsar_app_config": {
                    "tool_dependency_dir": "none",
                    "conda_auto_init": False,
                    "conda_auto_install": False,
                    **runner.get("pulsar_app_config", {}),
                },
            },
        },
        "execution": {
            "default": "remote_environment",
            "environments": {
                "local": {"runner": "local"},
                "remote_environment": {
                    "runner": "remote",
                    "remote_metadata": True,
                    "crypt4gh_recryptor_url": recryptor_url,
                    **environment,
                },
            },
        },
        "tools": [{"id": "__DATA_FETCH__", "environment": "local"}],
        "limits": [{"type": "walltime", "value": "48:00:00"}],
    }


def _configure_pulsar(config: dict[str, Any]) -> None:
    config["object_store_store_by"] = "uuid"
    # Outputs are staged to the remote job directory instead.
    config["outputs_to_working_directory"] = False


class TestCrypt4GHPulsarEmbeddedIntegration(test_crypt4gh_execution.TestCrypt4GHExecutionIntegration):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        _configure_pulsar(config)
        config["job_config"] = _pulsar_job_config(
            cls.service.url,
            # Tools write outputs in the remote job directory, like without a shared filesystem.
            {"default_file_action": "copy"},
            {"load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner"},
        )


class TestCrypt4GHPulsarEmbeddedMQIntegration(test_crypt4gh_execution.TestCrypt4GHExecutionIntegration):
    """Like :class:`TestCrypt4GHPulsarEmbeddedIntegration`, staging files through Galaxy's job files API.

    $ GALAXY_TEST_AMQP_URL='amqp://guest:guest@localhost:5672//' pytest test/integration/test_pulsar_embedded_crypt4gh.py
    """

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        if AMQP_URL is None:
            pytest.skip("External AMQP URL not configured for test")
        super().handle_galaxy_config_kwds(config)
        _configure_pulsar(config)
        jobs_directory = os.path.join(cls._test_driver.mkdtemp(), "pulsar_staging")
        safe_makedirs(jobs_directory)
        config["job_config"] = _pulsar_job_config(
            cls.service.url,
            {
                "default_file_action": "remote_transfer",
                "rewrite_parameters": True,
                "dependency_resolution": "none",
                "jobs_directory": jobs_directory,
                "remote_property_galaxy_home": os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir),
            },
            {
                "load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedMQJobRunner",
                "amqp_url": AMQP_URL,
                "pulsar_app_config": {"message_queue_url": AMQP_URL, "staging_directory": jobs_directory},
            },
        )
        config["galaxy_infrastructure_url"] = "http://localhost:$GALAXY_WEB_PORT"

    @pytest.mark.skip(
        reason="With remote_transfer, the outputs only used to discover others stay queued, for unprotected jobs too."
    )
    def test_every_kind_of_output_is_encrypted(self, history_id):
        pass


class TestCrypt4GHPulsarUnsafeDestinationIntegration(test_crypt4gh_execution.BaseCrypt4GHExecutionIntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        _configure_pulsar(config)
        config["job_config"] = _pulsar_job_config(
            cls.service.url,
            {
                "default_file_action": "copy",
                # Tools would write decrypted outputs directly to the object store.
                "file_actions": {"paths": [{"path_types": "output", "action": "none"}]},
                # The protection plan would hold paths of the Galaxy server.
                "rewrite_parameters": False,
            },
            {"load": "galaxy.jobs.runners.pulsar:PulsarEmbeddedJobRunner"},
        )

    def test_destination_that_cannot_protect_outputs_is_refused(self, history_id):
        dataset = self._upload_authorized(history_id, test_crypt4gh_execution.PLAINTEXT_1)
        job, output = self._wait_for_job(history_id, self._run_cat(history_id, dataset))
        assert job["state"] == "error"
        assert "tools must write outputs into the job directory" in output["misc_info"]
        assert "Pulsar destinations must use rewrite_parameters" in output["misc_info"]
        assert self.service.requests == []

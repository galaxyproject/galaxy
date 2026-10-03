"""Remote tool evaluation with separate Galaxy and Pulsar job directories."""

import os

import pytest

from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model import Job
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class TestPulsarRemoteToolEvaluation(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = os.path.join(
            os.path.dirname(__file__), "embedded_pulsar_remote_tool_eval_job_conf.yml"
        )
        config["metadata_strategy"] = "extended"
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False
        config["cleanup_job"] = "never"

    @pytest.mark.parametrize(
        "tool_id",
        [
            "job_properties",
            "simple_constructs",
            "version_command_tool_dir",
            "environment_variables",
            "composite",
            "metadata_bam",
            "column_param_configfile",
        ],
    )
    def test_tool_evaluation(self, tool_id):
        self._run_tool_test(tool_id)

    def test_deferred_input(self, test_http_server):
        populator = DatasetPopulator(self.galaxy_interactor)
        with populator.test_history() as history_id:
            uri = test_http_server.get_url(
                remote_url="https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
                file_path="test-data/1.bed",
            )
            dataset = populator.create_deferred_hda(history_id, uri=uri, ext="bed")
            response = populator.run_tool(
                "cat1", inputs={"input1": {"src": "hda", "id": dataset["id"]}}, history_id=history_id
            )
            populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            content = populator.get_history_dataset_content(history_id, dataset_id=response["outputs"][0]["id"])
            with open("test-data/1.bed") as source:
                assert content == source.read()
            job = self._app.model.session.get(Job, self._app.security.decode_id(response["jobs"][0]["id"]))
            assert job is not None
            galaxy_job_directory = JobWorkingDirectory(job, self._app.object_store).resolve()
            assert not os.path.exists(os.path.join(galaxy_job_directory, "inputs"))
            assert job.command_line
            assert galaxy_job_directory not in job.command_line
            assert populator.get_history_dataset_details(history_id, dataset_id=dataset["id"])["state"] == "deferred"

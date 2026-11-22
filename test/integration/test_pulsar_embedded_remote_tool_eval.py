"""Remote tool evaluation with separate Galaxy and Pulsar job directories."""

import os
import re

import pytest

from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model import Job
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.dirname(__file__)
TOOL_IDS = [
    "job_properties",
    "simple_constructs",
    "version_command_tool_dir",
    "environment_variables",
    "composite",
    "metadata_bam",
    "column_param_configfile",
    # The command template reads an input and a config file through their Pulsar paths.
    "command_reads_input_size",
    "command_reads_configfile",
    # Expression tool reading its input with load_contents.
    "param_value_from_file",
    # Source paths of datasets, collection elements and their metadata files in a configfile.
    "inputs_as_json_with_staging_paths",
]


class TestPulsarRemoteToolEvaluation(integration_util.IntegrationTestCase):
    framework_tool_and_types = True
    job_config_file = "embedded_pulsar_remote_tool_eval_job_conf.yml"
    metadata_strategy = "extended"

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = os.path.join(SCRIPT_DIRECTORY, cls.job_config_file)
        config["metadata_strategy"] = cls.metadata_strategy
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False
        config["cleanup_job"] = "never"

    @pytest.mark.parametrize("tool_id", TOOL_IDS)
    def test_tool_evaluation(self, tool_id):
        self._run_tool_test(tool_id)

    def test_command_line_recorded(self):
        job = self._run_input_size_job()
        assert job.command_line
        assert re.search(r"echo '(\d+) \1' > '", job.command_line)

    def test_object_store_configuration_not_sent(self):
        job = self._run_input_size_job()
        galaxy_job_directory = JobWorkingDirectory(job, self._app.object_store).resolve()
        pulsar_job_directory = os.path.join(self._app.config.data_dir, "pulsar_staging", str(job.id))
        for job_directory in (galaxy_job_directory, pulsar_job_directory):
            assert os.path.exists(os.path.join(job_directory, "metadata", "outputs_new", "compute_environment.json"))
            assert not os.path.exists(os.path.join(job_directory, "metadata", "outputs_new", "object_store_conf.json"))
            # Extended metadata collection writes outputs through the object store.
            assert os.path.exists(os.path.join(job_directory, "metadata", "object_store_conf.json")) == (
                self.metadata_strategy == "extended"
            )

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
            # Galaxy creates inputs/ for every job; the deferred input is materialized on the Pulsar side.
            assert not os.listdir(os.path.join(galaxy_job_directory, "inputs"))
            assert job.command_line
            assert galaxy_job_directory not in job.command_line
            assert populator.get_history_dataset_details(history_id, dataset_id=dataset["id"])["state"] == "deferred"

    def _run_input_size_job(self) -> Job:
        populator = DatasetPopulator(self.galaxy_interactor)
        with populator.test_history() as history_id:
            dataset = populator.new_dataset(history_id, content="abc", ext="txt", wait=True)
            response = populator.run_tool(
                "command_reads_input_size",
                inputs={"input1": {"src": "hda", "id": dataset["id"]}},
                history_id=history_id,
            )
            job_id = response["jobs"][0]["id"]
            populator.wait_for_job(job_id, assert_ok=True)
        job = self._app.model.session.get(Job, self._app.security.decode_id(job_id))
        assert job is not None
        return job


class TestPulsarRemoteToolEvaluationDirectoryMetadata(TestPulsarRemoteToolEvaluation):
    job_config_file = "embedded_pulsar_remote_tool_eval_directory_metadata_job_conf.yml"
    metadata_strategy = "directory"

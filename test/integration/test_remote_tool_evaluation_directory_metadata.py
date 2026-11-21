"""Remote tool evaluation on the local runner with the directory metadata strategy."""

import os

import pytest

from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.metadata import (
    job_metadata_directory,
    REMOTE_COMMAND_LINE_FILE,
)
from galaxy.model import Job
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

TOOL_IDS = [
    "job_properties",
    "simple_constructs",
    "composite",
    "metadata_bam",
    "column_param_configfile",
    "command_reads_input_size",
    "command_reads_configfile",
    "param_value_from_file",
]


class TestRemoteToolEvaluationDirectoryMetadata(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["metadata_strategy"] = "directory"
        config["tool_evaluation_strategy"] = "remote"
        config["retry_metadata_internally"] = False
        config["cleanup_job"] = "never"

    def test_command_line_built_in_job(self):
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
            working_directory = JobWorkingDirectory(job, self._app.object_store).resolve()
            with open(os.path.join(job_metadata_directory(working_directory), REMOTE_COMMAND_LINE_FILE)) as fh:
                assert fh.read() == job.command_line

    @pytest.mark.parametrize("tool_id", TOOL_IDS)
    def test_tool_evaluation(self, tool_id):
        self._run_tool_test(tool_id)

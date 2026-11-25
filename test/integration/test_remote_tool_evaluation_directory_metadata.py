"""Remote tool evaluation on the local runner with the directory metadata strategy."""

import os

import pytest

from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.metadata import (
    job_metadata_directory,
    REMOTE_COMMAND_LINE_FILE,
)
from galaxy.model import Job
from galaxy.tool_util_models import UserToolSource
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
USER_TOOL = {
    "class": "GalaxyUserTool",
    "id": "remote_eval_user_tool",
    "version": "1.0.0",
    "name": "remote_eval_user_tool",
    "container": "busybox",
    # A parameter reference and a JavaScript expression.
    "shell_command": "cat '$(inputs.input.path)' > output.txt && echo '$(1 + 1)' >> output.txt",
    "inputs": [{"name": "input", "type": "data", "format": "txt"}],
    "outputs": [{"name": "output", "type": "data", "format": "txt", "from_work_dir": "output.txt"}],
}
# /api/tools jobs have no tool_state, tool requests (/api/jobs) evaluate the validated tool state.
USER_TOOL_APIS = ["tools", "tool_request"]


def run_user_defined_tool(app, populator: DatasetPopulator, api: str, content: str = "abc\n") -> Job:
    with populator.test_history() as history_id, populator.user_tool_execute_permissions():
        dynamic_tool = populator.create_unprivileged_tool(UserToolSource(**USER_TOOL))
        dataset = populator.new_dataset(history_id, content=content, ext="txt", wait=True)
        inputs = {"input": {"src": "hda", "id": dataset["id"]}}
        if api == "tools":
            response = populator.run_tool_raw(None, inputs, history_id, tool_uuid=dynamic_tool["uuid"])
            response.raise_for_status()
            job_id = response.json()["jobs"][0]["id"]
        else:
            response = populator.tool_request_raw(None, inputs, history_id, tool_uuid=dynamic_tool["uuid"])
            response.raise_for_status()
            tool_request_id = response.json()["tool_request_id"]
            assert populator.wait_on_tool_request(tool_request_id)
            job_id = populator.galaxy_interactor.jobs_for_tool_request(tool_request_id)[0]["id"]
        populator.wait_for_job(job_id, assert_ok=True)
        output = populator.get_history_dataset_details(history_id)
        assert populator.get_history_dataset_content(history_id, dataset_id=output["id"]) == f"{content}2\n"
    job = app.model.session.get(Job, app.security.decode_id(job_id))
    assert job is not None
    assert bool(job.tool_state) == (api == "tool_request")
    return job


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

    @pytest.mark.parametrize("api", USER_TOOL_APIS)
    def test_user_defined_tool(self, api):
        job = run_user_defined_tool(self._app, DatasetPopulator(self.galaxy_interactor), api)
        input_hda = job.input_datasets[0].dataset
        assert input_hda
        assert job.command_line == f"cat '{input_hda.get_file_name()}' > output.txt && echo '2' >> output.txt"

    @pytest.mark.parametrize("api", USER_TOOL_APIS)
    def test_user_defined_tool_empty_input(self, api):
        run_user_defined_tool(self._app, DatasetPopulator(self.galaxy_interactor), api, content="")

    def test_user_defined_tool_reads_composite_input_extra_files(self):
        populator = DatasetPopulator(self.galaxy_interactor)
        with populator.test_history() as history_id:
            velvet_hda = populator.fetch_hda(
                history_id,
                {
                    "src": "composite",
                    "ext": "velvet",
                    "composite": {
                        "items": [
                            {"src": "pasted", "paste_content": "sequences content"},
                            {"src": "pasted", "paste_content": "roadmaps content"},
                            {"src": "pasted", "paste_content": "log content"},
                        ]
                    },
                },
                wait=True,
            )
            result = populator.run_tool(
                "composite_user_defined", {"input1": {"src": "hda", "id": velvet_hda["id"]}}, history_id
            )
            populator.wait_for_job(result["jobs"][0]["id"], assert_ok=True)
            output = populator.get_history_dataset_content(history_id, dataset_id=result["outputs"][0]["id"])
            assert output.strip() == "roadmaps content"

    @pytest.mark.parametrize("tool_id", TOOL_IDS)
    def test_tool_evaluation(self, tool_id):
        self._run_tool_test(tool_id)

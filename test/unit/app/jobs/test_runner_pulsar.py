import os
import re
from typing import (
    Any,
    cast,
)

import pytest
from pulsar.client.action_mapper import FileActionMapper
from pulsar.client.path_mapper import PathMapper

from galaxy.app_unittest_utils.tools_support import UsesTools
from galaxy.job_execution.compute_environment import (
    dataset_path_to_extra_path,
    SharedComputeEnvironment,
)
from galaxy.jobs.runners.pulsar import (
    _tool_provided_metadata_client_outputs,
    PulsarComputeEnvironment,
)
from galaxy.model.store.discover import InvalidDiscoveredFilePathError
from galaxy.util.unittest import TestCase

INTERACTIVE_TOOL = """
<tool id="interactive_tool" name="Interactive Tool" tool_type="interactive" version="$version" profile="$profile">
    <entry_points>
        <entry_point name="Interactive Tool"><port>8080</port></entry_point>
    </entry_points>
    <outputs />
</tool>
"""
TOOL_WITH_EXTERNAL_METADATA_PATH = """
<tool id="external_metadata" name="External Metadata" version="$version" profile="$profile">
    <command>echo test</command>
    <inputs />
    <outputs provided_metadata_file="../outside.json" />
</tool>
"""


class TestPulsarToolProvidedMetadataClientOutputs(TestCase, UsesTools):
    def setUp(self):
        self.setup_app()
        cast(Any, self.app.config).interactivetools_enable = True
        self.tool_working_directory = os.path.join(self.test_directory, "working")
        os.makedirs(self.tool_working_directory)

    def tearDown(self):
        self.tear_down_app()

    def test_only_requests_enabled_tool_provided_metadata(self):
        enabled_tool = self._init_tool(profile="26.1", filename="enabled.xml")
        disabled_tool = self._init_tool(
            INTERACTIVE_TOOL,
            profile="26.1",
            filename="disabled.xml",
        )

        enabled_dynamic_output, enabled_file_sources = _tool_provided_metadata_client_outputs(
            enabled_tool, self.tool_working_directory
        )
        disabled_dynamic_output, disabled_file_sources = _tool_provided_metadata_client_outputs(
            disabled_tool, self.tool_working_directory
        )

        assert enabled_dynamic_output == re.escape("galaxy.json")
        assert enabled_file_sources == [{"path": "galaxy.json", "type": "galaxy"}]
        assert disabled_dynamic_output is None
        assert disabled_file_sources == []

    def test_rejects_metadata_path_outside_working_directory(self):
        tool = self._init_tool(
            TOOL_WITH_EXTERNAL_METADATA_PATH,
            profile="26.1",
            filename="external.xml",
        )

        with pytest.raises(InvalidDiscoveredFilePathError):
            _tool_provided_metadata_client_outputs(tool, self.tool_working_directory)


# Under a `none` action, extra files resolve from the job's local dataset path,
# as the local runner's SharedComputeEnvironment resolves them. That path
# differs from where Galaxy keeps the dataset here (as it does under
# outputs_to_working_directory), so the tests can tell the two apart.
GALAXY_INPUT = "/galaxy/objects/dataset_1.dat"
JOB_INPUT = "/galaxy/jobs/1/inputs/dataset_1.dat"
GALAXY_OUTPUT = "/galaxy/objects/dataset_2.dat"
JOB_OUTPUT = "/galaxy/jobs/1/outputs/dataset_2.dat"

REMOTE_JOB_CONFIG = {
    "inputs_directory": "/remote/staging/inputs",
    "outputs_directory": "/remote/staging/outputs",
    "working_directory": "/remote/staging/working",
    "unstructured_files_directory": "/remote/staging/unstructured",
    "configs_directory": "/remote/staging/configs",
    "system_properties": {"separator": "/"},
}

FILE_ACTION_CONFIGS = {
    "none": {"default_action": "none"},
    "transfer": {"default_action": "transfer"},
    "rewrite": {
        "default_action": "none",
        "paths": [
            {
                "path": "/galaxy/jobs/",
                "action": "rewrite",
                "source_directory": "/galaxy/jobs/",
                "destination_directory": "/mnt/galaxy/jobs/",
            }
        ],
    },
}


class _StubJobIO:
    def get_input_path(self, dataset):
        return {GALAXY_INPUT: JOB_INPUT}[dataset.get_file_name()]

    def get_output_path(self, dataset):
        return {GALAXY_OUTPUT: JOB_OUTPUT}[dataset.get_file_name()]


class _StubDataset:
    def __init__(self, file_name):
        self.file_name = file_name
        self.extra_files_path = dataset_path_to_extra_path(file_name)

    def get_file_name(self):
        return self.file_name


def _compute_environment(file_actions):
    # Skip __init__, which needs a live Pulsar client and job wrapper; only the
    # attributes the extra-files rewrites read are set here.
    compute_environment = PulsarComputeEnvironment.__new__(PulsarComputeEnvironment)
    compute_environment.local_path_config = SharedComputeEnvironment(cast(Any, _StubJobIO()), cast(Any, None))
    compute_environment.path_mapper = PathMapper(
        None,
        REMOTE_JOB_CONFIG,
        "/galaxy/jobs/1/working",
        action_mapper=FileActionMapper(config=FILE_ACTION_CONFIGS[file_actions]),
    )
    compute_environment.path_rewrites_input_extra = {}
    return compute_environment


@pytest.mark.parametrize(
    "file_actions, expected_path, staged",
    [
        ("none", "/galaxy/jobs/1/inputs/dataset_1_files", False),
        ("transfer", "/remote/staging/inputs/dataset_1_files", True),
        ("rewrite", "/mnt/galaxy/jobs/1/inputs/dataset_1_files", True),
    ],
)
def test_input_extra_files_rewrite(file_actions, expected_path, staged):
    compute_environment = _compute_environment(file_actions)
    dataset = _StubDataset(GALAXY_INPUT)

    assert compute_environment.input_extra_files_rewrite(dataset) == expected_path
    expected_rewrites = {dataset.extra_files_path: expected_path} if staged else {}
    assert compute_environment.path_rewrites_input_extra == expected_rewrites


@pytest.mark.parametrize(
    "file_actions, expected_path",
    [
        ("none", "/galaxy/jobs/1/outputs/dataset_2_files"),
        ("transfer", "/remote/staging/outputs/dataset_2_files"),
        ("rewrite", "/mnt/galaxy/jobs/1/outputs/dataset_2_files"),
    ],
)
def test_output_extra_files_rewrite(file_actions, expected_path):
    compute_environment = _compute_environment(file_actions)
    dataset = _StubDataset(GALAXY_OUTPUT)

    assert compute_environment.output_extra_files_rewrite(dataset) == expected_path

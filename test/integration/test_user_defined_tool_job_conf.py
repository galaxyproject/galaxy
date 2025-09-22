"""Integration tests for user defined tools with Pulsar embedded runner."""

import os

import yaml

from galaxy.tool_util_models import UserToolSource
from galaxy_test.api.test_tools import TestsTools
from galaxy_test.base.populators import (
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_job_conf.yml")
EMBEDDED_PULSAR_TPV_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_tpv_job_conf.yml")
TOOL_WITH_RESOURCE_SPECIFICATION = yaml.safe_load(
    """class: GalaxyUserTool
id: resource_requirement
version: "0.1"
name: resource_requirement
description: test resource requirement
container: busybox
requirements:
  - type: resource
    ram_min: 2
  - type: resource
    cores_min: 2
shell_command: |
  echo $MEM > galaxy_memory_mb.txt && echo $CORES > galaxy_cores.txt
outputs:
  - name: output1
    type: data
    format: txt
    from_work_dir: galaxy_memory_mb.txt
  - name: output2
    type: data
    format: txt
    from_work_dir: galaxy_cores.txt
"""
)


class TestUserDefinedToolRecommendedJobSetup(integration_util.IntegrationTestCase, TestsTools):
    """Exercies how user defined tools could be run in production."""

    framework_tool_and_types = True
    job_config_file = EMBEDDED_PULSAR_JOB_CONFIG_FILE
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = cls.job_config_file
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "directory"
        config["admin_users"] = "udt@galaxy.org"

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_user_defined_runs_in_correct_destination(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            # Create a new dynamic tool.
            # This is a shell command tool that will echo the input dataset.
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            # Run tool.
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
            response = self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
                wait_for_job=True,
                assert_ok=True,
            )

            output_content = self.dataset_populator.get_history_dataset_content(history_id)
            assert output_content == "abc\n"
            with self._different_user(email="udt@galaxy.org"):
                destination_params = self._get(f"/api/jobs/{response['jobs'][0]['id']}/destination_params").json()

        assert destination_params["Runner"] == "pulsar_embed"


class TestUserDefinedToolRecommendedJobSetupTPV(TestUserDefinedToolRecommendedJobSetup):

    job_config_file = EMBEDDED_PULSAR_TPV_JOB_CONFIG_FILE

    def test_user_defined_applies_resource_requirements(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            # Create a new dynamic tool.
            # This is a shell command tool that will echo the input dataset.
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(
                UserToolSource(**TOOL_WITH_RESOURCE_SPECIFICATION)
            )
            # Run tool.
            response = self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={},
                wait_for_job=True,
                assert_ok=True,
            )
            memory, cores = response["outputs"]
            memory_content = self.dataset_populator.get_history_dataset_content(history_id, content_id=memory["id"])
            assert memory_content == "2.0\n"
            cores_content = self.dataset_populator.get_history_dataset_content(history_id, content_id=cores["id"])
            assert cores_content == "2.0\n"

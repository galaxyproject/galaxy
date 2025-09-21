"""Integration tests for user defined tools with Pulsar embedded runner."""

import os

from galaxy.tool_util_models import UserToolSource
from galaxy_test.api.test_tools import TestsTools
from galaxy_test.base.populators import (
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
)
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_job_conf.yml")


class TestUserDefinedToolRecommendedJobSetup(integration_util.IntegrationTestCase, TestsTools):
    """Exercies how user defined tools could be run in production."""

    framework_tool_and_types = True
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE
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
        assert destination_params["require_container"]

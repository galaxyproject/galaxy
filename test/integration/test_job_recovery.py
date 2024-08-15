"""Integration tests for the job recovery after server restarts."""

import os

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
DELAY_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "delay_job_conf.yml")
SIMPLE_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "simple_job_conf.xml")


class TestJobRecoveryBeforeHandledIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE
        config["server_name"] = "moo"

    def handle_reconfigure_galaxy_config_kwds(self, config) -> None:
        config["server_name"] = "main"

    def test_recovery(self) -> None:
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.run_tool_raw(
            "exit_code_oom",
            {},
            history_id,
        )
        self.restart(handle_reconfig=self.handle_reconfigure_galaxy_config_kwds)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)


class TestJobRecoveryAfterHandledIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = DELAY_JOB_CONFIG_FILE

    def handle_reconfigure_galaxy_config_kwds(self, config) -> None:
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE

    def test_recovery(self) -> None:
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.run_tool_raw(
            "exit_code_oom",
            {},
            history_id,
        )
        self.restart(handle_reconfig=self.handle_reconfigure_galaxy_config_kwds)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

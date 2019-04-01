"""Integration tests for the job recovery after server restarts."""

import os

from base import integration_util  # noqa: I202
from base.populators import (
    DatasetPopulator,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
DELAY_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "delay_job_conf.xml")
SIMPLE_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "simple_job_conf.xml")


class JobRecoveryBeforeHandledIntegerationTestCase(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    def setUp(self):
        super(JobRecoveryBeforeHandledIntegerationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE
        config["server_name"] = "moo"

    def handle_reconfigure_galaxy_config_kwds(self, config):
        config["server_name"] = "main"

    def test_recovery(self):
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.run_tool(
            "exit_code_oom",
            {},
            history_id,
            assert_ok=False,
        ).json()
        self.restart(handle_reconfig=self.handle_reconfigure_galaxy_config_kwds)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)


class JobRecoveryAfterHandledIntegerationTestCase(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    def setUp(self):
        super(JobRecoveryAfterHandledIntegerationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = DELAY_JOB_CONFIG_FILE

    def handle_reconfigure_galaxy_config_kwds(self, config):
        config["job_config_file"] = SIMPLE_JOB_CONFIG_FILE

    def test_recovery(self):
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.run_tool(
            "exit_code_oom",
            {},
            history_id,
            assert_ok=False,
        ).json()
        self.restart(handle_reconfig=self.handle_reconfigure_galaxy_config_kwds)
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

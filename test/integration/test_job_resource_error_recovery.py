import os

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
JOB_RESOURCES_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "dummy_job_resource_parameters.xml")
JOB_CONFIG = os.path.join(SCRIPT_DIRECTORY, "job_resource_error_recovery_job_conf.yml")


class TestJobRecoveryBeforeHandledIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_CONFIG
        config["job_resource_params_file"] = JOB_RESOURCES_CONFIG_FILE

    def test_recovers_from_job_resource_errors(self):
        with self.dataset_populator.test_history() as history_id:
            self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
steps:
  simple_step:
    tool_id: create_2
    tool_state:
      __job_resource:
        __job_resource__select: 'yes'
        cores: '32'
""",
                history_id=history_id,
            )

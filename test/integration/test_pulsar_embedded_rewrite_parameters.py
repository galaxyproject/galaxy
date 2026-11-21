"""Run tools on the embedded Pulsar runner with ``rewrite_parameters: true``.

The command template of some tools reads inputs and config files through their
rewritten Pulsar paths while Galaxy builds the command.
"""

import os

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_rewrite_parameters_job_conf.yml")


class TestEmbeddedPulsarRewriteParametersIntegrationInstance(integration_util.IntegrationTestCase):
    framework_tool_and_types = True
    dataset_populator: DatasetPopulator

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "directory"
        config["retry_metadata_internally"] = False

    def test_staged_files_removed_when_command_building_fails(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="abc\n", ext="txt", wait=True)
            run_response = self.dataset_populator.run_tool(
                "command_fails_after_reading_input",
                inputs={"input1": {"src": "hda", "id": dataset["id"]}},
                history_id=history_id,
            )
            job_id = run_response["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(job_id, assert_ok=False)
            output = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=run_response["outputs"][0]["id"], assert_ok=False
            )
            assert output["state"] == "error"
        pulsar_job_directory = os.path.join(
            self._app.config.data_dir, "pulsar_staging", str(self._app.security.decode_id(job_id))
        )
        assert not os.path.exists(pulsar_job_directory)


instance = integration_util.integration_module_instance(TestEmbeddedPulsarRewriteParametersIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        "command_reads_input_size",
        "command_reads_configfile",
        "cat_default",
        "composite",
        "simple_constructs",
        "multi_data_param",
        "column_param_configfile",
        "environment_variables",
    ]
)

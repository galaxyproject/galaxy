"""Integration tests for the Pulsar embedded runner with remote extended metadata and rewritten parameters."""

import os

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(
    SCRIPT_DIRECTORY, "embedded_pulsar_metadata_extended_rewrite_parameters_job_conf.yml"
)


class EmbeddedExtendedMetadataRewriteParametersPulsarIntegrationInstance(integration_util.IntegrationInstance):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE
        config["object_store_store_by"] = "uuid"
        config["metadata_strategy"] = "extended"
        config["retry_metadata_internally"] = False


class TestEmbeddedExtendedMetadataRewriteParametersPulsar(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        EmbeddedExtendedMetadataRewriteParametersPulsarIntegrationInstance.handle_galaxy_config_kwds(config)

    def test_from_work_dir_output_not_written_is_empty(self):
        populator = DatasetPopulator(self.galaxy_interactor)
        with populator.test_history() as history_id:
            result = populator.run_tool(
                "from_work_dir_glob_output_written", {"stray_files": 0, "write_output": False}, history_id
            )
            populator.wait_for_job(result["jobs"][0]["id"], assert_ok=True)
            output_id = result["outputs"][0]["id"]
            output = populator.get_history_dataset_details(history_id, dataset_id=output_id, wait=False)
            assert output["state"] == "ok"
            assert populator.get_history_dataset_content(history_id, dataset_id=output_id) == ""


instance = integration_util.integration_module_instance(
    EmbeddedExtendedMetadataRewriteParametersPulsarIntegrationInstance
)

test_tools = integration_util.integration_tool_runner(
    [
        "from_work_dir_glob",
        "from_work_dir_glob_output_written",
        "simple_constructs",
    ]
)

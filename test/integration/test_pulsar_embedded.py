"""Integration tests for the Pulsar embedded runner."""

import os

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_job_conf.yml")


class TestEmbeddedPulsarIntegrationInstance(integration_util.IntegrationTestCase):
    """Describe a Galaxy test instance with embedded pulsar configured."""

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

    def test_tool_eval_failure(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="ABC", ext="tabular")
            self.dataset_populator.run_tool(
                "gx_data_column",
                inputs={"ref_parameter": {"src": "hda", "id": dataset["id"]}, "parameter": 2},
                history_id=history_id,
            )
            failed_dataset = self.dataset_populator.get_history_dataset_details(history_id, wait=True, assert_ok=False)
            assert failed_dataset["state"] == "error"
            assert failed_dataset["misc_info"] == "Parameter 'parameter': requires a value, but no legal values defined"


instance = integration_util.integration_module_instance(TestEmbeddedPulsarIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        "cat_default",
        "cat_user_defined",
        "collection_nested_default",
        "collection_creates_dynamic_nested_from_json",
        "composite",
        "simple_constructs",
        "multi_data_param",
        "output_filter",
        "vcf_bgzip_test",
        "environment_variables",
        "multi_output_assign_primary_ext_dbkey",
        "job_properties",
        "strict_shell",
        "tool_provided_metadata_9",
        "simple_constructs_y",
        "composite_output",
        "composite_output_tests",
        "detect_errors",
        "tool_directory_copy",
        "metadata_columns",
        "create_directory_index",
    ]
)

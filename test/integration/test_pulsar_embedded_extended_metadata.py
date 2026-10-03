"""Integration tests for the Pulsar embedded runner with remote metadata."""

import os

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_metadata_extended_job_conf.yml")


class EmbeddedAndExtendedMetadataPulsarIntegrationInstance(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE
        config["object_store_store_by"] = "uuid"
        config["metadata_strategy"] = "extended"
        config["retry_metadata_internally"] = False


class TestEmbeddedAndExtendedMetadataPulsarRuntimeEnvironment(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        EmbeddedAndExtendedMetadataPulsarIntegrationInstance.handle_galaxy_config_kwds(config)

    def test_runtime_environment_warning(self):
        populator = DatasetPopulator(self.galaxy_interactor)
        with populator.test_history() as history_id:
            result = populator.run_tool("runtime_environment", {}, history_id)
            populator.wait_for_history(history_id, assert_ok=True)
            job = populator.get_job_details(result["jobs"][0]["id"], full=True).json()
            warnings = [m for m in job["job_messages"] if m["type"] == "runtime_environment_warning"]
            assert len(warnings) == 1
            assert warnings[0]["variable_names"] == ["EMPTY_VAR", "MISSING_VAR"]
            assert job["state"] == "ok"


instance = integration_util.integration_module_instance(EmbeddedAndExtendedMetadataPulsarIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        "version_command_plain",
        "version_command_tool_dir",
        "simple_constructs",
        "metadata_bam",
        "job_properties",
        "from_work_dir_glob",
        "gx_group_tag",
    ]
)

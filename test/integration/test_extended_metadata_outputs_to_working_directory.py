"""Integration tests for the Pulsar embedded runner."""

from galaxy_test.driver import integration_util
from .test_extended_metadata import (
    ExtendedMetadataIntegrationInstance,
    TEST_TOOL_IDS,
)


class ExtendedMetadataOutputsToWorkingDirIntegrationInstance(ExtendedMetadataIntegrationInstance):
    """Describe a Galaxy test instance with metadata_strategy set to extended and outputs_to_working_dir set."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "extended"
        config["object_store_store_by"] = "uuid"
        config["outpus_to_working_dir"] = True
        config["retry_metadata_internally"] = False


instance = integration_util.integration_module_instance(ExtendedMetadataOutputsToWorkingDirIntegrationInstance)

test_tools = integration_util.integration_tool_runner(TEST_TOOL_IDS)

"""Integration tests for the Pulsar embedded runner with remote metadata."""

import os

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


instance = integration_util.integration_module_instance(EmbeddedAndExtendedMetadataPulsarIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        "simple_constructs",
        "metadata_bam",
        # "job_properties",  # https://github.com/galaxyproject/galaxy/issues/11813
        "from_work_dir_glob",
    ]
)

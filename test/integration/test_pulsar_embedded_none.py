"""Integration tests for the Pulsar embedded runner with default_file_action: none.

This tests the configuration where Pulsar and Galaxy share a filesystem and
no file staging is needed (default_file_action: none).

See https://github.com/galaxyproject/galaxy/issues/21566
"""

import os

from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_none_job_conf.yml")


class EmbeddedNonePulsarIntegrationInstance(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured with default_file_action: none."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False


instance = integration_util.integration_module_instance(EmbeddedNonePulsarIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        "simple_constructs",
        "job_properties",
    ]
)

"""Integration tests for the Pulsar embedded runner with outputs to working directory."""

import os

from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_job_conf.yml")


class EmbeddedCopyWorkingPulsarIntegrationInstance(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE
        config["outputs_to_working_directory"] = True


instance = integration_util.integration_module_instance(EmbeddedCopyWorkingPulsarIntegrationInstance)

test_tools = integration_util.integration_tool_runner(["output_format", "output_filter"])

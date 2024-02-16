"""Integration tests for the Pulsar embedded runner."""

import os

from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_job_conf.yml")


class EmbeddedPulsarIntegrationInstance(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE


instance = integration_util.integration_module_instance(EmbeddedPulsarIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
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
    ]
)

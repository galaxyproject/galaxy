"""Run tools on the embedded Pulsar runner with ``rewrite_parameters: true``.

The command template of some tools reads inputs and config files while Galaxy
builds the command, before Pulsar has staged them.
"""

import os

from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
EMBEDDED_PULSAR_JOB_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "embedded_pulsar_rewrite_parameters_job_conf.yml")


class TestEmbeddedPulsarRewriteParametersIntegrationInstance(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = EMBEDDED_PULSAR_JOB_CONFIG_FILE
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "directory"
        config["retry_metadata_internally"] = False


instance = integration_util.integration_module_instance(TestEmbeddedPulsarRewriteParametersIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        # These run where Pulsar stages files after Galaxy has built the command.
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

"""Integration tests for the Pulsar embedded runner with outputs posted back to Galaxy's job files API."""

from galaxy_test.driver import integration_util
from .test_job_files_tus import EmbeddedPulsarJobFilesIntegrationInstance


class EmbeddedPulsarRemoteTransferIntegrationInstance(EmbeddedPulsarJobFilesIntegrationInstance):
    default_file_action = "remote_transfer"


instance = integration_util.integration_module_instance(EmbeddedPulsarRemoteTransferIntegrationInstance)

test_tools = integration_util.integration_tool_runner(["simple_constructs", "composite_output_tests"])

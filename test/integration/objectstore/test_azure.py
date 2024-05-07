from galaxy.util.unittest_utils import skip_unless_environ
from galaxy_test.driver import integration_util
from ._base import BaseAzureObjectStoreIntegrationTestCase

TEST_TOOL_IDS = [
    "multi_output",
    "multi_output_configured",
    "multi_output_assign_primary",
    "multi_output_recurse",
    "tool_provided_metadata_1",
    "tool_provided_metadata_2",
    "tool_provided_metadata_3",
    "tool_provided_metadata_4",
    "tool_provided_metadata_5",
    "tool_provided_metadata_6",
    "tool_provided_metadata_7",
    "tool_provided_metadata_8",
    "tool_provided_metadata_9",
    "tool_provided_metadata_10",
    "tool_provided_metadata_11",
    "tool_provided_metadata_12",
    "composite_output",
    "composite_output_tests",
    "metadata",
    "metadata_bam",
    "output_format",
    "output_auto_format",
]


class TestAzureObjectStoreIntegration(BaseAzureObjectStoreIntegrationTestCase):
    pass


instance = integration_util.integration_module_instance(TestAzureObjectStoreIntegration)
test_tools = integration_util.integration_tool_runner(TEST_TOOL_IDS)

skip_unless_environ("GALAXY_TEST_AZURE_CONTAINER_NAME")(test_tools)
skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_KEY")(test_tools)
skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_NAME")(test_tools)

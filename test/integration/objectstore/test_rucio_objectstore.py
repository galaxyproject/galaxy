from galaxy_test.driver import integration_util
from ._base import BaseRucioObjectStoreIntegrationTestCase

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


class TestRucioObjectStoreIntegration(BaseRucioObjectStoreIntegrationTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "directory"


instance = integration_util.integration_module_instance(TestRucioObjectStoreIntegration)
test_tools = integration_util.integration_tool_runner(TEST_TOOL_IDS)

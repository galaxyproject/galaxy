"""Integration tests for the flush_per_n_datasets setting."""
from galaxy_test.driver import integration_util


class FlushPerNDatasetsTestCase(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["flush_per_n_datasets"] = 1


instance = integration_util.integration_module_instance(FlushPerNDatasetsTestCase)
test_tools = integration_util.integration_tool_runner(
    ["collection_creates_dynamic_nested", "collection_creates_dynamic_list_of_pairs"]
)

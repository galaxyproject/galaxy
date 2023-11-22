from galaxy_test.driver import integration_util


class StoreByIdTestCase(integration_util.IntegrationInstance):
    """Describe a Galaxy test instance with embedded pulsar configured."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_store_by"] = "id"
        config["outputs_to_working_directory"] = True


instance = integration_util.integration_module_instance(StoreByIdTestCase)

test_tools = integration_util.integration_tool_runner(
    [
        "composite_output_tests",
    ]
)

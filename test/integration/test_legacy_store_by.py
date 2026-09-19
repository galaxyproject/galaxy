from galaxy_test.api.test_workflows import ChangeDatatypeTests
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util


class TestChangeDatatypeStoreByIdIntegration(integration_util.IntegrationTestCase, ChangeDatatypeTests):
    """Test changing datatype with object_store_store_by: id."""

    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_store_by"] = "id"
        config["retry_metadata_internally"] = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)


class StoreByIdIntegrationInstance(integration_util.IntegrationInstance):
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_store_by"] = "id"
        config["outputs_to_working_directory"] = True


instance = integration_util.integration_module_instance(StoreByIdIntegrationInstance)

test_tools = integration_util.integration_tool_runner(
    [
        "composite_output_tests",
    ]
)

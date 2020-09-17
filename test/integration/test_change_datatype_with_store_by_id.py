from galaxy_test.api.test_workflows import ChangeDatatypeTestCase
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util


class ChangeDatatypeStoreByIdIntegrationTestCase(integration_util.IntegrationTestCase, ChangeDatatypeTestCase):
    """Test changing datatype with object_store_store_by: id."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["object_store_store_by"] = "id"
        config["retry_metadata_internally"] = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

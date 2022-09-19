from galaxy_test.api.test_tools import TestsTools
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    uses_test_history,
)
from galaxy_test.driver import integration_util


class ExtendedMetadataMappingIntegrationTestCase(integration_util.IntegrationTestCase, TestsTools):
    """Test mapping over tools with extended metadata enabled."""

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["metadata_strategy"] = "extended"
        config["object_store_store_by"] = "uuid"
        config["retry_metadata_internally"] = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @uses_test_history()
    def test_map_over_collection(self, history_id):
        hdca_id = self._build_pair(history_id, ["123", "456"])
        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        self._run_and_check_simple_collection_mapping(history_id, inputs)

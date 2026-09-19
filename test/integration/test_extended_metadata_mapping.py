from galaxy_test.api.test_tools import TestsTools
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util


class TestExtendedMetadataMappingIntegration(integration_util.IntegrationTestCase, TestsTools):
    """Test mapping over tools with extended metadata enabled."""

    dataset_populator: DatasetPopulator
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

    def test_map_over_collection(self, history_id):
        hdca_id = self._build_pair(history_id, ["123", "456"])
        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        self._run_and_check_simple_collection_mapping(history_id, inputs)

    def _run_and_check_simple_collection_mapping(self, history_id, inputs):
        create = self._run_cat(history_id, inputs=inputs, assert_ok=True)
        outputs = create["outputs"]
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 2
        assert len(outputs) == 2
        assert len(implicit_collections) == 1
        output1 = outputs[0]
        output2 = outputs[1]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        output2_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output2)
        assert output1_content.strip() == "123"
        assert output2_content.strip() == "456"

from typing import Optional

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class TestDatasetHashingIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    calculate_dataset_hash: Optional[str] = None

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        if cls.calculate_dataset_hash is not None:
            config["enable_celery_tasks"] = True
            config["calculate_dataset_hash"] = cls.calculate_dataset_hash

    def test_hashing(self, history_id: str) -> None:
        hda = self.dataset_populator.new_dataset(history_id, wait=True)
        if self.calculate_dataset_hash in [None, "always", "upload"]:
            hashes = self.dataset_populator.wait_for_dataset_hashes(history_id=history_id, dataset_id=hda["id"])
            assert hashes[0]["hash_value"] == "a17dcdfd36f47303a4824f1309d43ac14d7491ab3b8abb28782ac8e8d3b680ea"
        else:
            assert hda["hashes"] == [], hda
        inputs = {"input1": {"src": "hda", "id": hda["id"]}}
        run_response = self.dataset_populator.run_tool_raw("cat1", inputs=inputs, history_id=history_id)
        self.dataset_populator.wait_for_tool_run(history_id=history_id, run_response=run_response)
        cat_dataset = self.dataset_populator.get_history_dataset_details(history_id=history_id)
        if self.calculate_dataset_hash == "always":
            hashes = self.dataset_populator.wait_for_dataset_hashes(history_id=history_id, dataset_id=cat_dataset["id"])
            assert hashes[0]["hash_value"] == "a17dcdfd36f47303a4824f1309d43ac14d7491ab3b8abb28782ac8e8d3b680ea"
        else:
            assert cat_dataset["hashes"] == [], cat_dataset


class TestDatasetHashingAlwaysIntegration(TestDatasetHashingIntegration):
    calculate_dataset_hash = "always"


class TestDatasetHashingUploadIntegration(TestDatasetHashingIntegration):
    calculate_dataset_hash = "upload"


class TestDatasetHashingNeverIntegration(TestDatasetHashingIntegration):
    calculate_dataset_hash = "never"

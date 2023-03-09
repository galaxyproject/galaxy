from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestRecalculateUserDiskUsageIntegration(IntegrationTestCase):
    task_based = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True

    def test_recalculate_user_disk_usage(self):
        # The initial disk usage is 0
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == 0
        size = 100
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content=f"{'0'*size}", wait=True)["id"]
        expected_usage = size + 1  # +1 for the new line character in the dataset
        # The usage should be the total of the datasets
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == expected_usage
        self.dataset_populator.delete_dataset(history_id, hda_id, purge=True, wait_for_purge=True)

        # Purging that dataset should result in usage dropping back
        # down to zero.
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == 0

        recalculate_response = self._put("users/current/recalculate_disk_usage")
        task_ok = self.dataset_populator.wait_on_task(recalculate_response)
        assert task_ok

        # The disk usage should be 0 again
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == 0

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestDiskUsageUpdateDefault(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_run_work_dir_glob(self, history_id):
        # Run a tool with a work dir glob and ensure content and disk usage is updated.
        self.dataset_populator.new_dataset(history_id, content="fwd1Test", wait=True)
        initial_disk_usage = self.dataset_populator.total_disk_usage()
        response = self.dataset_populator.run_tool("from_work_dir_glob", {}, history_id, assert_ok=True)
        self.dataset_populator.wait_for_job(job_id=response["jobs"][0]["id"])
        final_disk_usage = self.dataset_populator.total_disk_usage()
        assert final_disk_usage == initial_disk_usage + 3


class TestDiskUsageCeleryExtended(TestDiskUsageUpdateDefault):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["metadata_strategy"] = "celery_extended"

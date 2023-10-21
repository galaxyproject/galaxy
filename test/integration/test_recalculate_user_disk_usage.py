import string
import time

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase
from .objectstore._base import BaseObjectStoreIntegrationTestCase
from .objectstore.test_selection_with_resource_parameters import DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE

SIMPLE_DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
<object_store type="distributed" id="primary" order="0">
    <backends>
        <backend id="default" type="disk" weight="1" name="Default Store">
            <description>This is my description of the default store with *markdown*.</description>
            <files_dir path="${temp_directory}/files_default"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_default"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_default"/>
        </backend>
        <backend id="static" type="disk" weight="0">
            <files_dir path="${temp_directory}/files_static"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_static"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_static"/>
        </backend>
    </backends>
</object_store>
"""
)


class RecalculateDiskUsage:
    task_based: bool
    dataset_populator: DatasetPopulator

    def test_recalculate_user_disk_usage(self):
        # The initial disk usage is 0
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == 0
        size = 100
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content=f"{'0' * size}", wait=True)["id"]
        expected_usage = size + 1  # +1 for the new line character in the dataset
        # The usage should be the total of the datasets
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == expected_usage

        self.recalculate_disk_usage()
        # The disk usage should still be the expected usage
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == expected_usage

        self.dataset_populator.delete_dataset(history_id, hda_id, purge=True, wait_for_purge=True)

        # Purging that dataset should result in usage dropping back
        # down to zero.
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == 0

        self.recalculate_disk_usage()
        # The disk usage should be 0 again
        current_usage = self.dataset_populator.get_usage_for(None)
        assert current_usage["total_disk_usage"] == 0

    def recalculate_disk_usage(self):
        recalculate_response = self.dataset_populator._put("users/current/recalculate_disk_usage")
        if self.task_based:
            task_ok = self.dataset_populator.wait_on_task(recalculate_response)
            assert task_ok
        else:
            time.sleep(2)


class TestRecalculateUserDiskUsageIntegration(IntegrationTestCase, RecalculateDiskUsage):
    task_based = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True


class TestRecalculateUserDiskUsageHierarchicalIntegration(BaseObjectStoreIntegrationTestCase, RecalculateDiskUsage):
    task_based = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True


class TestRecalculateUserDiskUsageSimpleHierarchicalIntegration(
    BaseObjectStoreIntegrationTestCase, RecalculateDiskUsage
):
    task_based = True
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(SIMPLE_DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True


class TestRecalculateUserDiskUsageHierarchicalNoTaskIntegration(
    BaseObjectStoreIntegrationTestCase, RecalculateDiskUsage
):
    task_based = False
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "extended"

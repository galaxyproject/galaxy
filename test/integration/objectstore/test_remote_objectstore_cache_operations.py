import os
import shutil

import pytest

from galaxy_test.base.populators import skip_without_tool
from ._base import (
    BaseSwiftObjectStoreIntegrationTestCase,
    files_count,
    get_files,
)


class TestCacheOperation(BaseSwiftObjectStoreIntegrationTestCase):
    def tearDown(self):
        shutil.rmtree(self.object_store_cache_path)
        os.mkdir(self.object_store_cache_path)
        return super().tearDown()

    def upload_dataset(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="123", wait=True)
        return hda

    def upload_bam_dataset(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(
            history_id, content=open(self.test_data_resolver.get_filename("1.bam"), "rb"), file_type="bam", wait=True
        )
        return hda

    def test_cache_populated(self):
        self.upload_dataset()
        assert files_count(self.object_store_cache_path) == 1

    def test_cache_repopulated(self):
        hda = self.upload_dataset()
        assert files_count(self.object_store_cache_path) == 1
        shutil.rmtree(self.object_store_cache_path)
        os.mkdir(self.object_store_cache_path)
        assert files_count(self.object_store_cache_path) == 0
        content = self.dataset_populator.get_history_dataset_content(hda["history_id"], content_id=hda["id"])
        assert content == "123\n"
        assert files_count(self.object_store_cache_path) == 1

    def test_cache_repopulated_metadata_file(self):
        hda = self.upload_bam_dataset()
        assert files_count(self.object_store_cache_path) == 2
        response = self._get(
            f'histories/{hda["history_id"]}/contents/{hda["id"]}/metadata_file?metadata_file=bam_index'
        )
        assert len(response.content) > 0
        response.raise_for_status()
        shutil.rmtree(self.object_store_cache_path)
        assert files_count(self.object_store_cache_path) == 0
        response = self._get(
            f'histories/{hda["history_id"]}/contents/{hda["id"]}/metadata_file?metadata_file=bam_index'
        )
        response.raise_for_status()
        assert files_count(self.object_store_cache_path) == 1
        assert len(response.content) > 0

    def test_delete_item_not_in_cache(self):
        hda = self.upload_dataset()
        assert files_count(self.object_store_cache_path) == 1
        shutil.rmtree(self.object_store_cache_path)
        os.mkdir(self.object_store_cache_path)
        assert files_count(self.object_store_cache_path) == 0
        self.dataset_populator.delete_dataset(hda["history_id"], hda["id"], purge=True, wait_for_purge=True)
        # Don't wait for dataset, this uses the history state, which is new if there is no dataset ...
        with pytest.raises(AssertionError) as excinfo:
            self.dataset_populator.get_history_dataset_content(
                hda["history_id"], content_id=hda["id"], wait=False, assert_ok=False
            )
            assert "File Not Found" in str(excinfo.value)

    def test_upload_updates_cache(self):
        self.upload_dataset()
        assert files_count(self.object_store_cache_path) == 1
        only_file = next(iter(get_files(self.object_store_cache_path)))
        assert os.path.getsize(only_file) == 4


class TestCacheOperationWithNoCacheUpdate(BaseSwiftObjectStoreIntegrationTestCase):
    @classmethod
    def updateCacheData(cls):
        return False

    def tearDown(self):
        shutil.rmtree(self.object_store_cache_path)
        os.mkdir(self.object_store_cache_path)
        return super().tearDown()

    @skip_without_tool("create_2")
    def test_cache_populated_after_tool_run(self):
        history_id = self.dataset_populator.new_history()
        running_response = self.dataset_populator.run_tool_raw(
            "create_2",
            {"sleep_time": 0},
            history_id,
        )
        result = self.dataset_populator.wait_for_tool_run(
            run_response=running_response, history_id=history_id, assert_ok=False
        ).json()
        details = self.dataset_populator.get_job_details(result["jobs"][0]["id"], full=True).json()
        assert details["state"] == "ok"
        # check files in the cache are empty after job finishes (they are created by Galaxy before the tool executes)
        assert files_count(self.object_store_cache_path) == 2
        hda1_details = self.dataset_populator.get_history_dataset_details(history_id, assert_ok=True, hid=1)
        hda2_details = self.dataset_populator.get_history_dataset_details(history_id, assert_ok=True, hid=2)
        assert os.path.getsize(hda1_details["file_name"]) == 0
        assert os.path.getsize(hda2_details["file_name"]) == 0
        # get dataset content - this should trigger pulling to the cache
        content1 = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=hda1_details["dataset_id"])
        content2 = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=hda2_details["dataset_id"])
        assert content1 == "1\n"
        assert content2 == "2\n"
        # check files in the cache are not empty now
        assert os.path.getsize(hda1_details["file_name"]) != 0
        assert os.path.getsize(hda2_details["file_name"]) != 0

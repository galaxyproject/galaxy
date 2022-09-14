import os
import shutil

import pytest

from ._base import (
    BaseSwiftObjectStoreIntegrationTestCase,
    files_count,
)


class CacheOperationTestCase(BaseSwiftObjectStoreIntegrationTestCase):
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

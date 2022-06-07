import zipfile
from io import BytesIO

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    uses_test_history,
)
from galaxy_test.driver.integration_util import IntegrationTestCase


class AsyncDownloadsIntegrationTestCase(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @uses_test_history(require_new=True)
    def test_async_collection_download(self, history_id):
        fetch_response = self.dataset_collection_populator.create_list_in_history(history_id, direct_upload=True).json()
        dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        returned_dce = dataset_collection["elements"]
        assert len(returned_dce) == 3, dataset_collection
        download_async_response = self._download_dataset_collection_async(
            history_id=history_id, hdca_id=dataset_collection["id"]
        )
        download_contents = self.dataset_populator.wait_on_download(download_async_response)
        archive = zipfile.ZipFile(BytesIO(download_contents.content))
        namelist = archive.namelist()
        assert len(namelist) == 3, f"Expected 3 elements in [{namelist}]"
        collection_name = dataset_collection["name"]
        for element, zip_path in zip(returned_dce, namelist):
            assert f"{collection_name}/{element['element_identifier']}.{element['object']['file_ext']}" == zip_path

    def _download_dataset_collection_async(self, history_id, hdca_id):
        return self._post(f"histories/{history_id}/contents/dataset_collections/{hdca_id}/prepare_download")

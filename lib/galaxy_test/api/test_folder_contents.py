from typing import List

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    LibraryPopulator,
)
from ._framework import ApiTestCase


class FolderContentsApiTestCase(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

        self.history_id = self.dataset_populator.new_history()
        self.library = self.library_populator.new_private_library("FolderContentsTestsLibrary")
        self.root_folder = self._create_folder_in_library("Test Folder Contents", self.library)
        self.root_folder_id = self.root_folder["id"]

    def test_create_hda_with_ldda_message(self):
        hda_id = self._create_hda()
        ldda_message = "Test message"
        data = {
            "from_hda_id": hda_id,
            "ldda_message": ldda_message,
        }
        ldda = self._create_content_in_folder_with_payload(self.root_folder_id, data)
        self._assert_has_keys(ldda, "name", "id")

    def test_create_hdca_with_ldda_message(self):
        contents = ["dataset01", "dataset02"]
        hdca_id = self._create_hdca_with_contents(contents)
        ldda_message = "Test message"
        data = {
            "from_hdca_id": hdca_id,
            "ldda_message": ldda_message,
        }
        lddas = self._create_content_in_folder_with_payload(self.root_folder_id, data)
        assert len(contents) == len(lddas)

    def test_index(self):
        folder = self._create_folder_in_library("Test Folder Contents Index", self.library)
        folder_id = folder["id"]

        self._create_dataset_in_folder(folder_id)

        response = self._get(f"folders/{folder_id}/contents")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == 1

    def test_index_include_deleted(self):
        folder_name = "Test Folder Contents Index include deleted"
        folder = self._create_folder_in_library(folder_name, self.library)
        folder_id = folder["id"]

        hda_id = self._create_dataset_in_folder(folder_id)
        self._delete_library_dataset(hda_id)

        response = self._get(f"folders/{folder_id}/contents")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == 0

        include_deleted = True
        response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == 1
        assert contents[0]["deleted"] is True

    def test_index_limit_offset(self):
        folder_name = "Test Folder Contents Index limit"
        folder = self._create_folder_in_library(folder_name, self.library)
        folder_id = folder["id"]

        num_datasets = 5
        for _ in range(num_datasets):
            self._create_dataset_in_folder(folder_id)

        response = self._get(f"folders/{folder_id}/contents")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == num_datasets

        limit = 3
        response = self._get(f"folders/{folder_id}/contents?limit={limit}")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == limit

        offset = 3
        response = self._get(f"folders/{folder_id}/contents?offset={offset}")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == num_datasets - offset

        limit = 2
        offset = 2
        response = self._get(f"folders/{folder_id}/contents?limit={limit}&offset={offset}")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == limit

    def _create_folder_in_library(self, name: str, library):
        root_folder_id = library["root_folder_id"]
        data = {
            "name": name,
            "description": f"The description of {name}",
        }
        create_response = self._post(f"folders/{root_folder_id}", data=data)
        self._assert_status_code_is(create_response, 200)
        folder = create_response.json()
        return folder

    def _create_dataset_in_folder(self, folder_id):
        hda_id = self._create_hda()
        data = {
            "from_hda_id": hda_id,
        }
        ldda = self._create_content_in_folder_with_payload(folder_id, data)
        return ldda["id"]

    def _create_content_in_folder_with_payload(self, folder_id, payload):
        create_response = self._post(f"folders/{folder_id}/contents", data=payload)
        self._assert_status_code_is(create_response, 200)
        return create_response.json()

    def _create_hda(self):
        hda = self.dataset_populator.new_dataset(self.history_id)
        hda_id = hda["id"]
        return hda_id

    def _create_hdca_with_contents(self, contents: List[str]):
        hdca = self.dataset_collection_populator.create_list_in_history(self.history_id, contents=contents, direct_upload=True).json()["outputs"][0]
        hdca_id = hdca["id"]
        return hdca_id

    def _delete_library_dataset(self, ldda_id):
        delete_response = self._delete(f"libraries/datasets/{ldda_id}", admin=True)
        self._assert_status_code_is(delete_response, 200)

from typing import (
    Any,
    List,
    Optional,
)

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
        self.root_folder_id = self._create_folder_in_library("Test Folder Contents")

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
        folder_id = self._create_folder_in_library("Test Folder Contents Index")

        self._create_dataset_in_folder(folder_id)

        response = self._get(f"folders/{folder_id}/contents")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == 1

    def test_index_include_deleted(self):
        folder_name = "Test Folder Contents Index include deleted"
        folder_id = self._create_folder_in_library(folder_name)

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
        folder_id = self._create_folder_in_library(folder_name)

        num_subfolders = 5
        for index in range(num_subfolders):
            self._create_subfolder_in(folder_id, name=f"Folder_{index}")

        num_datasets = 5
        for _ in range(num_datasets):
            self._create_dataset_in_folder(folder_id)

        total_items = num_datasets + num_subfolders

        response = self._get(f"folders/{folder_id}/contents")
        self._assert_status_code_is(response, 200)
        original_contents = response.json()["folder_contents"]
        assert len(original_contents) == total_items

        limit = 7
        response = self._get(f"folders/{folder_id}/contents?limit={limit}")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == limit

        offset = 3
        response = self._get(f"folders/{folder_id}/contents?offset={offset}")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == total_items - offset

        limit = 4
        offset = 4
        response = self._get(f"folders/{folder_id}/contents?limit={limit}&offset={offset}")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == limit
        expected_query_result = original_contents[offset : offset + limit]
        for index in range(limit):
            assert contents[index]["id"] == expected_query_result[index]["id"]

    def test_index_search_text(self):
        folder_name = "Test Folder Contents Index search text"
        folder_id = self._create_folder_in_library(folder_name)

        dataset_names = ["AB", "BC", "ABC"]
        for name in dataset_names:
            self._create_dataset_in_folder(folder_id, name)

        subfolder_names = ["Folder_A", "Folder_C"]
        for name in subfolder_names:
            self._create_subfolder_in(folder_id, name)

        all_names = dataset_names + subfolder_names

        search_terms = ["A", "B", "C"]
        for search_text in search_terms:
            response = self._get(f"folders/{folder_id}/contents?search_text={search_text}")
            self._assert_status_code_is(response, 200)
            contents = response.json()["folder_contents"]
            matching_names = [name for name in all_names if search_text in name]
            assert len(contents) == len(matching_names)

    def test_index_permissions_include_deleted(self):

        folder_name = "Test Folder Contents Index permissions include deteleted"
        folder_id = self._create_folder_in_library(folder_name)

        num_subfolders = 5
        subfolder_ids: List[str] = []
        deleted_subfolder_ids: List[str] = []
        for index in range(num_subfolders):
            id = self._create_subfolder_in(folder_id, name=f"Folder_{index}")
            subfolder_ids.append(id)

        for index, subfolder_id in enumerate(subfolder_ids):
            if index % 2 == 0:
                self._delete_subfolder(subfolder_id)
                deleted_subfolder_ids.append(subfolder_id)

        num_datasets = 5
        datasets_ids: List[str] = []
        deleted_datasets_ids: List[str] = []
        for _ in range(num_datasets):
            id = self._create_dataset_in_folder(folder_id)
            datasets_ids.append(id)

        for index, ldda_id in enumerate(datasets_ids):
            if index % 2 == 0:
                self._delete_library_dataset(ldda_id)
                deleted_datasets_ids.append(ldda_id)

        num_total_contents = num_subfolders + num_datasets
        num_non_deleted = num_total_contents - len(deleted_subfolder_ids) - len(deleted_datasets_ids)

        # Verify deleted contents are not listed
        include_deleted = False
        response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == num_non_deleted

        include_deleted = True
        # Admins can see everything...
        response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}", admin=True)
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == num_total_contents

        # Owner can see everything too
        response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}")
        self._assert_status_code_is(response, 200)
        contents = response.json()["folder_contents"]
        assert len(contents) == num_total_contents

        # Users with access but no modify permission can't see deleted
        with self._different_user():
            different_user_role_id = self.dataset_populator.user_private_role_id()

        self._allow_library_access_to_user_role(different_user_role_id)

        with self._different_user():
            response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}")
            self._assert_status_code_is(response, 200)
            contents = response.json()["folder_contents"]
            assert len(contents) == num_non_deleted

    def _create_folder_in_library(self, name: str) -> Any:
        root_folder_id = self.library["root_folder_id"]
        return self._create_subfolder_in(root_folder_id, name)

    def _create_subfolder_in(self, folder_id: str, name: str) -> str:
        data = {
            "name": name,
            "description": f"The description of {name}",
        }
        create_response = self._post(f"folders/{folder_id}", data=data, json=True)
        self._assert_status_code_is(create_response, 200)
        folder = create_response.json()
        return folder["id"]

    def _create_dataset_in_folder(self, folder_id: str, name: Optional[str] = None) -> str:
        hda_id = self._create_hda(name)
        data = {
            "from_hda_id": hda_id,
        }
        ldda = self._create_content_in_folder_with_payload(folder_id, data)
        return ldda["id"]

    def _create_content_in_folder_with_payload(self, folder_id: str, payload) -> Any:
        create_response = self._post(f"folders/{folder_id}/contents", data=payload, json=True)
        self._assert_status_code_is(create_response, 200)
        return create_response.json()

    def _create_hda(self, name: Optional[str] = None) -> str:
        hda = self.dataset_populator.new_dataset(self.history_id, name=name)
        hda_id = hda["id"]
        return hda_id

    def _create_hdca_with_contents(self, contents: List[str]) -> str:
        hdca = self.dataset_collection_populator.create_list_in_history(
            self.history_id, contents=contents, direct_upload=True, wait=True
        ).json()["outputs"][0]
        hdca_id = hdca["id"]
        return hdca_id

    def _delete_library_dataset(self, ldda_id: str) -> None:
        delete_response = self._delete(f"libraries/datasets/{ldda_id}")
        self._assert_status_code_is(delete_response, 200)

    def _delete_subfolder(self, folder_id: str) -> None:
        delete_response = self._delete(f"folders/{folder_id}")
        self._assert_status_code_is(delete_response, 200)

    def _allow_library_access_to_user_role(self, role_id: str):
        library_id = self.library["id"]
        action = "set_permissions"
        data = {
            "access_ids[]": role_id,
        }
        response = self._post(f"libraries/{library_id}/permissions?action={action}", data=data, admin=True, json=True)
        self._assert_status_code_is(response, 200)

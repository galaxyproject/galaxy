from typing import (
    Any,
    List,
    Optional,
    Tuple,
)

from galaxy_test.base.decorators import requires_new_library
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    LibraryPopulator,
)
from ._framework import ApiTestCase


class TestFolderContentsApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

        self.library = self.library_populator.new_private_library("FolderContentsTestsLibrary")
        self.root_folder_id = self._create_folder_in_library("Test Folder Contents")

    @requires_new_library
    def test_create_hda_with_ldda_message(self, history_id):
        hda_id = self._create_hda(history_id)
        ldda_message = "Test message"
        data = {
            "from_hda_id": hda_id,
            "ldda_message": ldda_message,
        }
        ldda = self._create_content_in_folder_with_payload(self.root_folder_id, data)
        self._assert_has_keys(ldda, "name", "id")

    @requires_new_library
    def test_create_hdca_with_ldda_message(self, history_id):
        contents = ["dataset01", "dataset02"]
        hdca_id = self._create_hdca_with_contents(history_id, contents)
        ldda_message = "Test message"
        data = {
            "from_hdca_id": hdca_id,
            "ldda_message": ldda_message,
        }
        lddas = self._create_content_in_folder_with_payload(self.root_folder_id, data)
        assert len(contents) == len(lddas)

    @requires_new_library
    def test_index(self, history_id):
        folder_id = self._create_folder_in_library("Test Folder Contents Index")

        self._create_subfolder_in(folder_id)
        self._create_dataset_in_folder(history_id, folder_id)

        response = self._get(f"folders/{folder_id}/contents")
        self._assert_index_count_is_correct(response, expected_contents_count=2)

    @requires_new_library
    def test_index_include_deleted(self, history_id):
        folder_name = "Test Folder Contents Index include deleted"
        folder_id = self._create_folder_in_library(folder_name)

        sub_folder_id = self._create_subfolder_in(folder_id)
        ldda_id, _ = self._create_dataset_in_folder(history_id, folder_id)
        self._delete_library_dataset(ldda_id)
        self._delete_subfolder(sub_folder_id)

        response = self._get(f"folders/{folder_id}/contents")
        self._assert_index_count_is_correct(response, expected_contents_count=0)

        include_deleted = True
        response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}")
        index_response = self._assert_index_count_is_correct(response, expected_contents_count=2)
        for content in index_response["folder_contents"]:
            assert content["deleted"] is True

    @requires_new_library
    def test_index_pagination(self, history_id):
        folder_name = "Test Folder Contents Pagination"
        folder_id = self._create_folder_in_library(folder_name)

        num_subfolders = 5
        for index in range(num_subfolders):
            self._create_subfolder_in(folder_id, name=f"Folder_{index}")

        num_datasets = 5
        for _ in range(num_datasets):
            self._create_dataset_in_folder(history_id, folder_id)

        total_items = num_datasets + num_subfolders

        response = self._get(f"folders/{folder_id}/contents")
        index_response = self._assert_index_count_is_correct(response, expected_contents_count=total_items)
        original_contents = index_response["folder_contents"]

        limit = 7
        response = self._get(f"folders/{folder_id}/contents?limit={limit}")
        index_response = self._assert_index_count_is_correct(
            response, expected_contents_count=limit, expected_total_count=total_items
        )

        limit = 20
        response = self._get(f"folders/{folder_id}/contents?limit={limit}")
        index_response = self._assert_index_count_is_correct(response, expected_contents_count=total_items)

        offset = 3
        response = self._get(f"folders/{folder_id}/contents?offset={offset}")
        index_response = self._assert_index_count_is_correct(
            response, expected_contents_count=total_items - offset, expected_total_count=total_items
        )

        offset = 20
        response = self._get(f"folders/{folder_id}/contents?offset={offset}")
        index_response = self._assert_index_count_is_correct(
            response, expected_contents_count=0, expected_total_count=total_items
        )

        limit = 4
        offset = 4
        response = self._get(f"folders/{folder_id}/contents?limit={limit}&offset={offset}")
        index_response = self._assert_index_count_is_correct(
            response, expected_contents_count=limit, expected_total_count=total_items
        )
        contents = index_response["folder_contents"]
        expected_query_result = original_contents[offset : offset + limit]
        for index in range(limit):
            assert contents[index]["id"] == expected_query_result[index]["id"]

        limit = 20
        offset = 6
        response = self._get(f"folders/{folder_id}/contents?limit={limit}&offset={offset}")
        actual_limit = limit if limit < total_items else total_items - offset
        index_response = self._assert_index_count_is_correct(
            response, expected_contents_count=actual_limit, expected_total_count=total_items
        )
        contents = index_response["folder_contents"]
        expected_query_result = original_contents[offset : offset + actual_limit]
        for index in range(actual_limit):
            assert contents[index]["id"] == expected_query_result[index]["id"]

    @requires_new_library
    def test_index_search_text(self, history_id):
        folder_name = "Test Folder Contents Index search text"
        folder_id = self._create_folder_in_library(folder_name)

        dataset_names = ["AB", "BX", "abx"]
        for name in dataset_names:
            self._create_dataset_in_folder(history_id, folder_id, name)

        subfolder_names = ["Folder_a", "Folder_X"]
        for name in subfolder_names:
            self._create_subfolder_in(folder_id, name)

        all_names = dataset_names + subfolder_names

        search_terms = ["A", "B", "X"]
        for search_text in search_terms:
            matching_names = [name for name in all_names if search_text.casefold() in name.casefold()]
            response = self._get(f"folders/{folder_id}/contents?search_text={search_text}")
            index_response = self._assert_index_count_is_correct(response, expected_contents_count=len(matching_names))
            contents = index_response["folder_contents"]
            for content in contents:
                assert search_text.casefold() in content["name"].casefold()

    @requires_new_library
    def test_index_permissions(self, history_id):
        folder_name = "Test Folder Contents Index permissions"
        folder_id = self._create_folder_in_library(folder_name)
        _, hda_id = self._create_dataset_in_folder(history_id, folder_id)

        self._make_dataset_private(hda_id)

        # Owner can access
        response = self._get(f"folders/{folder_id}/contents")
        self._assert_index_count_is_correct(response, expected_contents_count=1)

        # Admins can access
        response = self._get(f"folders/{folder_id}/contents", admin=True)
        self._assert_index_count_is_correct(response, expected_contents_count=1)

        # Other users can't access
        with self._different_user():
            # Without access to the parent library the user gets a 404... should it be a 403 instead?
            response = self._get(f"folders/{folder_id}/contents")
            self._assert_status_code_is(response, 404)

            # Grant library access to this user
            different_user_role_id = self.dataset_populator.user_private_role_id()
            self._allow_library_access_to_user_role(different_user_role_id)  # Runs as admin

            # The user can access the library folder but not the private dataset in it
            response = self._get(f"folders/{folder_id}/contents")
            self._assert_index_count_is_correct(response, expected_contents_count=0)

            # Grant access to this user
            self._allow_dataset_access(hda_id)
            response = self._get(f"folders/{folder_id}/contents")
            self._assert_index_count_is_correct(response, expected_contents_count=1)

    @requires_new_library
    def test_index_permissions_include_deleted(self, history_id) -> None:
        folder_name = "Test Folder Contents Index permissions include deleted"
        folder_id = self._create_folder_in_library(folder_name)

        num_subfolders = 5
        subfolder_ids: List[str] = []
        deleted_subfolder_ids: List[str] = []
        for index in range(num_subfolders):
            ldda_id = self._create_subfolder_in(folder_id, name=f"Folder_{index}")
            subfolder_ids.append(ldda_id)

        for index, subfolder_id in enumerate(subfolder_ids):
            if index % 2 == 0:
                self._delete_subfolder(subfolder_id)
                deleted_subfolder_ids.append(subfolder_id)

        num_datasets = 5
        ldda_ids: List[str] = []
        deleted_ldda_ids: List[str] = []
        for _ in range(num_datasets):
            ldda_id, _ = self._create_dataset_in_folder(history_id, folder_id)
            ldda_ids.append(ldda_id)

        for index, ldda_id in enumerate(ldda_ids):
            if index % 2 == 0:
                self._delete_library_dataset(ldda_id)
                deleted_ldda_ids.append(ldda_id)

        num_total_contents = num_subfolders + num_datasets
        num_non_deleted = num_total_contents - len(deleted_subfolder_ids) - len(deleted_ldda_ids)

        # Verify deleted contents are not listed
        include_deleted = False
        response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}")
        self._assert_index_count_is_correct(response, expected_contents_count=num_non_deleted)

        include_deleted = True
        # Admins can see everything...
        response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}", admin=True)
        self._assert_index_count_is_correct(response, expected_contents_count=num_total_contents)

        # Owner can see everything too
        response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}")
        self._assert_index_count_is_correct(response, expected_contents_count=num_total_contents)

        # Users with access but no modify permission can't see deleted
        with self._different_user():
            different_user_role_id = self.dataset_populator.user_private_role_id()

            self._allow_library_access_to_user_role(different_user_role_id)  # Runs as admin

            response = self._get(f"folders/{folder_id}/contents?include_deleted={include_deleted}")
            self._assert_index_count_is_correct(response, expected_contents_count=num_non_deleted)

    @requires_new_library
    def test_index_order_by(self, history_id):
        folder_name = "Test Folder Contents Index Order By"
        folder_id = self._create_folder_in_library(folder_name)

        subfolder_names = ["Folder_A", "Folder_B", "Folder_C"]
        subfolder_descriptions = ["Description Z", "Description Y", "Description X"]
        for index, name in enumerate(subfolder_names):
            self._create_subfolder_in(folder_id, name, subfolder_descriptions[index])

        dataset_names = ["a", "b", "c"]
        ldda_messages = ["Message Z", "Message Y", "Message X"]
        dataset_sizes = [50, 100, 10]
        file_types = ["txt", "csv", "json"]
        for index, name in enumerate(dataset_names):
            self._create_dataset_in_folder(
                history_id,
                folder_id,
                name,
                content=f"{'0'*dataset_sizes[index]}",
                ldda_message=ldda_messages[index],
                file_type=file_types[index],
            )

        # Wait for datasets to finish upload
        self.dataset_populator.wait_for_history(history_id)

        # Folders always have priority (they show-up before any dataset regardless of the sorting) and they
        # can only be sorted by name, description and update_time, the other sorting attributes are ignored
        sort_desc = False
        order_by = "name"
        expected_order_by_name = ["Folder_A", "Folder_B", "Folder_C", "a", "b", "c"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

        order_by = "description"
        expected_order_by_name = ["Folder_C", "Folder_B", "Folder_A", "c", "b", "a"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

        order_by = "type"
        expected_order_by_name = ["Folder_A", "Folder_B", "Folder_C", "b", "c", "a"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

        order_by = "size"
        expected_order_by_name = ["Folder_A", "Folder_B", "Folder_C", "c", "a", "b"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

        order_by = "update_time"
        expected_order_by_name = ["Folder_A", "Folder_B", "Folder_C", "a", "b", "c"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

        sort_desc = True
        order_by = "name"
        expected_order_by_name = ["Folder_C", "Folder_B", "Folder_A", "c", "b", "a"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

        order_by = "description"
        expected_order_by_name = ["Folder_A", "Folder_B", "Folder_C", "a", "b", "c"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

        order_by = "type"
        expected_order_by_name = ["Folder_A", "Folder_B", "Folder_C", "a", "c", "b"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

        order_by = "size"
        expected_order_by_name = ["Folder_A", "Folder_B", "Folder_C", "b", "a", "c"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

        order_by = "update_time"
        expected_order_by_name = ["Folder_C", "Folder_B", "Folder_A", "c", "b", "a"]
        self._assert_folder_order_by_is_expected(folder_id, order_by, sort_desc, expected_order_by_name)

    def _assert_folder_order_by_is_expected(
        self, folder_id: str, order_by: str, sort_desc: str, expected_order_by_name: List[str]
    ):
        response = self._get(f"folders/{folder_id}/contents?order_by={order_by}&sort_desc={sort_desc}")
        index_response = self._assert_index_count_is_correct(
            response, expected_contents_count=len(expected_order_by_name)
        )
        for index, item in enumerate(index_response["folder_contents"]):
            assert item["name"] == expected_order_by_name[index]

    def _assert_index_count_is_correct(
        self, raw_response, expected_contents_count: int, expected_total_count: Optional[int] = None
    ) -> dict:
        self._assert_status_code_is(raw_response, 200)
        if expected_total_count is None:
            expected_total_count = expected_contents_count
        index_response = raw_response.json()
        metadata = index_response["metadata"]
        contents = index_response["folder_contents"]
        assert metadata["total_rows"] == expected_total_count, "Expected total rows doesn't match"
        assert len(contents) == expected_contents_count, "Expected number of contents doesn't match"
        return index_response

    def _create_folder_in_library(self, name: str) -> str:
        root_folder_id = self.library["root_folder_id"]
        return self._create_subfolder_in(root_folder_id, name)

    def _create_subfolder_in(
        self, folder_id: str, name: Optional[str] = None, description: Optional[str] = None
    ) -> str:
        data = {
            "name": name or "Test Folder",
            "description": description or f"The description of {name}",
        }
        create_response = self._post(f"folders/{folder_id}", data=data, json=True)
        self._assert_status_code_is(create_response, 200)
        folder = create_response.json()
        return folder["id"]

    def _create_dataset_in_folder(
        self,
        history_id: str,
        folder_id: str,
        name: Optional[str] = None,
        content: Optional[str] = None,
        ldda_message: Optional[str] = None,
        **kwds,
    ) -> Tuple[str, str]:
        """Returns a tuple with the LDDA ID and the underlying HDA ID"""
        hda_id = self._create_hda(history_id, name, content, **kwds)
        data = {
            "from_hda_id": hda_id,
            "ldda_message": ldda_message or "Test msg",
        }
        ldda = self._create_content_in_folder_with_payload(folder_id, data)
        return ldda["id"], hda_id

    def _create_content_in_folder_with_payload(self, folder_id: str, payload) -> Any:
        create_response = self._post(f"folders/{folder_id}/contents", data=payload, json=True)
        self._assert_status_code_is(create_response, 200)
        return create_response.json()

    def _create_hda(self, history_id: str, name: Optional[str] = None, content: Optional[str] = None, **kwds) -> str:
        hda = self.dataset_populator.new_dataset(history_id, name=name, content=content, **kwds)
        hda_id = hda["id"]
        return hda_id

    def _create_hdca_with_contents(self, history_id: str, contents: List[str]) -> str:
        hdca = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=contents, direct_upload=True, wait=True
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

    def _allow_dataset_access(self, dataset_id: str):
        payload = {"action": "remove_restrictions"}
        update_response = self._put(f"datasets/{dataset_id}/permissions", payload, admin=True, json=True)
        self._assert_status_code_is_ok(update_response)

    def _make_dataset_private(self, dataset_id: str):
        payload = {"action": "make_private"}
        update_response = self._put(f"datasets/{dataset_id}/permissions", payload, json=True)
        self._assert_status_code_is_ok(update_response)

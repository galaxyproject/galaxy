from galaxy_test.base.decorators import requires_new_library
from galaxy_test.base.populators import (
    DatasetPopulator,
    LibraryPopulator,
)
from ._framework import ApiTestCase


class TestFoldersApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)
        self.library = self.library_populator.new_library("FolderTestsLibrary")

    @requires_new_library
    def test_create(self):
        folder = self._create_folder("Test Create Folder")
        self._assert_valid_folder(folder)
        # assert that listing items in folder works.
        # this is a regression test
        response = self._get(f"libraries/{folder['parent_library_id']}/contents")
        response.raise_for_status()

    @requires_new_library
    def test_list_library(self):
        library, _ = self.library_populator.fetch_single_url_to_folder()
        library = self._list_library(library["id"])
        assert len(library) == 2
        folders = [folder for folder in library if folder["type"] == "folder"]
        assert len(folders) == 1
        files = [file for file in library if file["type"] == "file"]
        assert len(files) == 1

    @requires_new_library
    def test_create_without_name_raises_400(self):
        root_folder_id = self.library["root_folder_id"]
        data = {
            "description": "Description only",
        }
        create_response = self._post(f"folders/{root_folder_id}", data=data, admin=True, json=True)
        self._assert_status_code_is(create_response, 400)

    @requires_new_library
    def test_permissions(self):
        folder = self._create_folder("Test Permissions Folder")
        folder_id = folder["id"]

        empty_permissions = self._get_permissions(folder_id)
        self._assert_permissions_empty(empty_permissions)

        role_id = self.library_populator.user_private_role_id()
        action = "set_permissions"
        data = {
            "add_ids[]": [role_id],
            "manage_ids[]": role_id,  # string-lists also supported
            "modify_ids[]": [role_id],
        }
        response = self._post(f"folders/{folder_id}/permissions?action={action}", data=data, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        new_permissions = response.json()

        permissions = self._get_permissions(folder_id)
        assert permissions == new_permissions
        self._assert_permissions_contains_role(permissions, role_id)

    @requires_new_library
    def test_update(self):
        folder = self._create_folder("Test Update Folder")
        folder_id = folder["id"]
        updated_name = "UPDATED"
        updated_desc = "UPDATED DESCRIPTION"
        data = {
            "name": updated_name,
            "description": updated_desc,
        }
        put_response = self._put(f"folders/{folder_id}", data=data, admin=True, json=True)
        self._assert_status_code_is(put_response, 200)
        updated_folder = put_response.json()
        self._assert_valid_folder(updated_folder)
        assert updated_folder["name"] == updated_name
        assert updated_folder["description"] == updated_desc

    @requires_new_library
    def test_delete(self):
        folder = self._create_folder("Test Delete Folder")
        folder_id = folder["id"]

        deleted_folder = self._delete_folder(folder_id)
        assert deleted_folder["deleted"] is True

    @requires_new_library
    def test_undelete(self):
        folder = self._create_folder("Test Undelete Folder")
        folder_id = folder["id"]

        deleted_folder = self._delete_folder(folder_id)
        assert deleted_folder["deleted"] is True

        undelete = True
        undelete_response = self._delete(f"folders/{folder_id}?undelete={undelete}", admin=True)
        self._assert_status_code_is(undelete_response, 200)
        undeleted_folder = undelete_response.json()
        assert undeleted_folder["deleted"] is False

    @requires_new_library
    def test_import_folder_to_history(self):
        library, response = self.library_populator.fetch_single_url_to_folder()
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        with self.dataset_populator.test_history() as history_id:
            create_data = {"source": "library_folder", "content": dataset["folder_id"]}
            create_response = self._post(f"histories/{history_id}/contents", create_data, json=True)
            create_response.raise_for_status()
            datasets = create_response.json()
            assert len(datasets) == 1
            assert datasets[0]["name"] == "4.bed"

    @requires_new_library
    def test_update_deleted_raise_403(self):
        folder = self._create_folder("Test Update Deleted Folder")
        folder_id = folder["id"]

        deleted_folder = self._delete_folder(folder_id)
        assert deleted_folder["deleted"] is True

        data = {
            "name": "test",
        }
        put_response = self._put(f"folders/{folder_id}", data=data, admin=True, json=True)
        self._assert_status_code_is(put_response, 403)

    def _list_library(self, library_id):
        response = self._get(f"libraries/{library_id}/contents")
        response.raise_for_status()
        return response.json()

    def _create_folder(self, name: str):
        root_folder_id = self.library["root_folder_id"]
        data = {
            "name": name,
            "description": f"The description of {name}",
        }
        create_response = self._post(f"folders/{root_folder_id}", data=data, admin=True, json=True)
        self._assert_status_code_is(create_response, 200)
        folder = create_response.json()
        return folder

    def _delete_folder(self, folder_id):
        delete_response = self._delete(f"folders/{folder_id}", admin=True)
        self._assert_status_code_is(delete_response, 200)
        deleted_folder = delete_response.json()
        return deleted_folder

    def _get_permissions(self, folder_id):
        response = self._get(f"folders/{folder_id}/permissions", admin=True)
        self._assert_status_code_is(response, 200)
        permissions = response.json()
        self._assert_valid_permissions(permissions)
        return permissions

    def _assert_valid_folder(self, folder):
        self._assert_has_keys(
            folder,
            "id",
            "name",
            "model_class",
            "parent_id",
            "item_count",
            "genome_build",
            "update_time",
            "deleted",
            "library_path",
            "parent_library_id",
        )

    def _assert_valid_permissions(self, permissions):
        self._assert_has_keys(
            permissions,
            "modify_folder_role_list",
            "manage_folder_role_list",
            "add_library_item_role_list",
        )

    def _assert_permissions_empty(self, permissions):
        assert permissions["modify_folder_role_list"] == []
        assert permissions["manage_folder_role_list"] == []
        assert permissions["add_library_item_role_list"] == []

    def _assert_permissions_contains_role(self, permissions, role_id):
        assert role_id in permissions["modify_folder_role_list"][0]
        assert role_id in permissions["manage_folder_role_list"][0]
        assert role_id in permissions["add_library_item_role_list"][0]

import unittest

from galaxy.model.unittest_utils.store_fixtures import (
    one_ld_library_model_store_dict,
    TEST_LIBRARY_NAME,
)
from galaxy.util.unittest_utils import skip_if_github_down
from galaxy_test.base import api_asserts
from galaxy_test.base.decorators import requires_new_library
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    FILE_URL,
    LibraryPopulator,
    skip_without_asgi,
)
from ._framework import ApiTestCase


class TestLibrariesApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

    @requires_new_library
    def test_create(self):
        data = dict(name="CreateTestLibrary")
        create_response = self._post("libraries", data=data, admin=True, json=True)
        self._assert_status_code_is(create_response, 200)
        library = create_response.json()
        self._assert_has_keys(library, "name")
        assert library["name"] == "CreateTestLibrary"

    @skip_without_asgi
    @requires_new_library
    def test_create_from_store(self):
        response = self.library_populator.create_from_store(store_dict=one_ld_library_model_store_dict())
        assert isinstance(response, list)
        assert len(response) == 1
        library_summary = response[0]
        assert library_summary["name"] == TEST_LIBRARY_NAME
        assert "id" in library_summary
        ld = self.library_populator.get_library_contents_with_path(library_summary["id"], "/my cool name")
        assert ld

    @requires_new_library
    def test_index(self):
        self.library_populator.new_library("TestIndexLibraries")
        libraries = self.library_populator.get_libraries()
        assert len(libraries) > 0

    @requires_new_library
    def test_delete(self):
        library = self.library_populator.new_library("DeleteTestLibrary")
        create_response = self._delete(f"libraries/{library['id']}", admin=True)
        self._assert_status_code_is(create_response, 200)
        library = create_response.json()
        self._assert_has_keys(library, "deleted")
        assert library["deleted"] is True
        # Test undeleting
        data = dict(undelete=True)
        create_response = self._delete(f"libraries/{library['id']}", data=data, admin=True, json=True)
        library = create_response.json()
        self._assert_status_code_is(create_response, 200)
        assert library["deleted"] is False

    def test_nonadmin(self):
        # Anons can't create libs
        data = dict(name="CreateTestLibrary")
        create_response = self._post("libraries", data=data, admin=False, anon=True)
        self._assert_status_code_is(create_response, 403)
        # Anons can't delete libs
        library = self.library_populator.new_library("AnonDeleteTestLibrary")
        create_response = self._delete(f"libraries/{library['id']}", admin=False, anon=True)
        self._assert_status_code_is(create_response, 403)
        # Anons can't update libs
        data = dict(name="ChangedName", description="ChangedDescription", synopsis="ChangedSynopsis")
        create_response = self._patch(f"libraries/{library['id']}", data=data, admin=False, anon=True, json=True)
        self._assert_status_code_is(create_response, 403)

    @requires_new_library
    def test_update(self):
        library = self.library_populator.new_library("UpdateTestLibrary")
        data = dict(name="ChangedName", description="ChangedDescription", synopsis="ChangedSynopsis")
        create_response = self._patch(f"libraries/{library['id']}", data=data, admin=True, json=True)
        self._assert_status_code_is(create_response, 200)
        library = create_response.json()
        self._assert_has_keys(library, "name", "description", "synopsis")
        assert library["name"] == "ChangedName"
        assert library["description"] == "ChangedDescription"
        assert library["synopsis"] == "ChangedSynopsis"

    @requires_new_library
    def test_update_non_admins_with_permission(self):
        library = self.library_populator.new_library("UpdateTestLibraryNonAdmin")
        library_id = library["id"]
        role_id = self.library_populator.user_private_role_id()
        data = dict(name="ChangedName", description="ChangedDescription", synopsis="ChangedSynopsis")
        # User has no permission by default
        create_response = self._patch(f"libraries/{library['id']}", data=data, json=True)
        self._assert_status_code_is(create_response, 403)
        # Grant modify permission
        self.library_populator.set_modify_permission(library_id, role_id)
        create_response = self._patch(f"libraries/{library['id']}", data=data, json=True)
        self._assert_status_code_is(create_response, 200)
        library = create_response.json()
        self._assert_has_keys(library, "name", "description", "synopsis")
        assert library["name"] == "ChangedName"
        assert library["description"] == "ChangedDescription"
        assert library["synopsis"] == "ChangedSynopsis"

    @requires_new_library
    def test_create_private_library_legacy_permissions(self):
        library = self.library_populator.new_library("LegacyPermissionTestLibrary")
        library_id = library["id"]
        role_id = self.library_populator.user_private_role_id()
        self.library_populator.set_permissions(library_id, role_id)
        create_response = self._create_folder(library)
        self._assert_status_code_is(create_response, 200)

        with self._different_user():
            create_response = self._create_folder(library)
            self._assert_status_code_is(create_response, 403)

    @requires_new_library
    def test_create_private_library_permissions(self):
        library = self.library_populator.new_library("PermissionTestLibrary")
        library_id = library["id"]
        role_id = self.library_populator.user_private_role_id()
        self.library_populator.set_permissions_with_action(library_id, role_id, action="set_permissions")
        create_response = self._create_folder(library)
        self._assert_status_code_is(create_response, 200)

        with self._different_user():
            create_response = self._create_folder(library)
            self._assert_status_code_is(create_response, 403)

    @requires_new_library
    def test_get_library_current_permissions(self):
        library = self.library_populator.new_library("GetCurrentPermissionTestLibrary")
        library_id = library["id"]
        current = self.library_populator.get_permissions(library_id, scope="current")
        self._assert_has_keys(
            current,
            "access_library_role_list",
            "modify_library_role_list",
            "manage_library_role_list",
            "add_library_item_role_list",
        )

        role_id = self.library_populator.user_private_role_id()
        self.library_populator.set_permissions_with_action(library_id, role_id, action="set_permissions")
        current = self.library_populator.get_permissions(library_id, scope="current")
        assert role_id in current["access_library_role_list"][0]
        assert role_id in current["modify_library_role_list"][0]
        assert role_id in current["manage_library_role_list"][0]
        assert role_id in current["add_library_item_role_list"][0]

    @requires_new_library
    def test_get_library_available_permissions(self):
        library = self.library_populator.new_library("GetAvailablePermissionTestLibrary")
        library_id = library["id"]
        role_id = self.library_populator.user_private_role_id()
        # As we can manage this library our role will be available
        available = self.library_populator.get_permissions(library_id, scope="available")
        available_role_ids = [role["id"] for role in available["roles"]]
        assert role_id in available_role_ids

    @requires_new_library
    def test_get_library_available_permissions_with_query(self):
        library = self.library_populator.new_library("GetAvailablePermissionWithQueryTestLibrary")
        library_id = library["id"]

        with self._different_user():
            email = self.library_populator.user_email()

        # test at least 2 user roles should be available now
        available = self.library_populator.get_permissions(library_id, scope="available")
        available_role_ids = [role["id"] for role in available["roles"]]
        assert len(available_role_ids) > 1

        # test query for specific role/email
        available = self.library_populator.get_permissions(library_id, scope="available", q=email)
        available_role_emails = [role["name"] for role in available["roles"]]
        assert available["total"] == 1
        assert available_role_emails[0] == email

    @requires_new_library
    def test_create_library_dataset_bootstrap_user(self, library_name="private_dataset", wait=True):
        library = self.library_populator.new_private_library(library_name)
        payload, files = self.library_populator.create_dataset_request(library, file_type="txt", contents="create_test")
        create_response = self.galaxy_interactor.post(
            f"libraries/{library['id']}/contents", payload, files=files, key=self.master_api_key
        )
        self._assert_status_code_is(create_response, 400)

    @requires_new_library
    def test_create_dataset_denied(self):
        url, payload = self._create_dataset_kwargs()
        with self._different_user():
            create_response = self._post(url, payload, json=True)
            self._assert_status_code_is(create_response, 403)

    @requires_new_library
    def test_create_dataset_bootstrap_admin_user(self):
        url, payload = self._create_dataset_kwargs()
        with self._different_user():
            create_response = self._post(url, payload, key=self.master_api_key, json=True)
            self._assert_status_code_is(create_response, 400)

    def _create_dataset_kwargs(self):
        library = self.library_populator.new_private_library("ForCreateDatasets")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]["id"]
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content="1 2 3")["id"]
        return f"folders/{folder_id}/contents", {"from_hda_id": hda_id}

    @requires_new_library
    def test_show_private_dataset_permissions(self):
        library, library_dataset = self.library_populator.new_library_dataset_in_private_library(
            "ForCreateDatasets", wait=True
        )
        with self._different_user():
            response = self.library_populator.show_ld_raw(library["id"], library_dataset["id"])
            api_asserts.assert_status_code_is(response, 403)
            api_asserts.assert_error_code_is(response, 403002)

    @requires_new_library
    def test_create_dataset(self):
        library, library_dataset = self.library_populator.new_library_dataset_in_private_library(
            "ForCreateDatasets", wait=True
        )
        self._assert_has_keys(library_dataset, "peek", "data_type")
        assert library_dataset["peek"].find("create_test") >= 0
        assert library_dataset["file_ext"] == "txt", library_dataset["file_ext"]
        # Get library dataset (same as library_dataset)
        library_dataset_from_show = self.library_populator.show_ld(library["id"], library_dataset["id"])
        assert library_dataset_from_show["id"] == library_dataset["id"]
        assert library_dataset_from_show["parent_library_id"] == library["id"]
        assert library_dataset_from_show["folder_id"] == library["root_folder_id"]
        # Get library dataset dataset association
        ldda = self.library_populator.show_ldda(library_dataset_from_show["ldda_id"])
        assert ldda["library_dataset_id"] == library_dataset["id"]
        assert ldda["parent_library_id"] == library["id"]
        assert ldda["file_ext"] == "txt"

    @requires_new_library
    def test_fetch_upload_to_folder(self):
        history_id, library, destination = self._setup_fetch_to_folder("flat_zip")
        items = [{"src": "files", "dbkey": "hg19", "info": "my cool bed", "created_from_basename": "4.bed"}]
        targets = [{"destination": destination, "items": items}]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
            "__files": {"files_0|file_data": open(self.test_data_resolver.get_filename("4.bed"))},
        }
        self.dataset_populator.fetch(payload, wait=True)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset
        assert dataset["genome_build"] == "hg19", dataset
        assert dataset["misc_info"] == "my cool bed", dataset
        assert dataset["file_ext"] == "bed", dataset
        assert dataset["created_from_basename"] == "4.bed"

    @requires_new_library
    def test_fetch_zip_to_folder(self):
        history_id, library, destination = self._setup_fetch_to_folder("flat_zip")
        bed_test_data_path = self.test_data_resolver.get_filename("4.bed.zip")
        targets = [
            {
                "destination": destination,
                "items_from": "archive",
                "src": "files",
            }
        ]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
            "__files": {"files_0|file_data": open(bed_test_data_path, "rb")},
        }
        self.dataset_populator.fetch(payload)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset

    @requires_new_library
    def test_fetch_single_url_to_folder(self):
        library, response = self.library_populator.fetch_single_url_to_folder()
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset

    @requires_new_library
    def test_fetch_single_url_with_invalid_datatype(self):
        _, response = self.library_populator.fetch_single_url_to_folder("xxx", assert_ok=False)
        self._assert_status_code_is(response, 400)
        assert response.json()["err_msg"] == "Requested extension 'xxx' unknown, cannot upload dataset."

    @requires_new_library
    def test_legacy_upload_unknown_datatype(self):
        library = self.library_populator.new_private_library("ForLegacyUpload")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]["id"]
        payload = {
            "folder_id": folder_id,
            "create_type": "file",
            "file_type": "xxx",
            "upload_option": "upload_file",
            "files_0|url_paste": FILE_URL,
        }
        create_response = self._post(f"libraries/{library['id']}/contents", payload, json=True)
        self._assert_status_code_is(create_response, 400)
        assert create_response.json()["err_msg"] == "Requested extension 'xxx' unknown, cannot upload dataset."

    @skip_if_github_down
    @requires_new_library
    def test_fetch_failed_validation(self):
        # Exception handling is really rough here - we should be creating a dataset in error instead
        # of just failing the job like this.
        history_id, library, destination = self._setup_fetch_to_folder("single_url")
        items = [
            {
                "src": "url",
                "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
                "MD5": "37b59762b59fff860460522d271bc112",
                "name": "4.bed",
            }
        ]
        targets = [
            {
                "destination": destination,
                "items": items,
            }
        ]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
        }
        tool_response = self.dataset_populator.fetch(payload, assert_ok=False)
        job = self.dataset_populator.check_run(tool_response)
        self.dataset_populator.wait_for_job(job["id"])

        job = tool_response.json()["jobs"][0]
        details = self.dataset_populator.get_job_details(job["id"]).json()
        assert details["state"] == "ok", details

        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["state"] == "error", dataset

    @skip_if_github_down
    @requires_new_library
    def test_fetch_url_archive_to_folder(self):
        history_id, library, destination = self._setup_fetch_to_folder("single_url")
        targets = [
            {
                "destination": destination,
                "items_from": "archive",
                "src": "url",
                "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed.zip",
            }
        ]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
        }
        self.dataset_populator.fetch(payload)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset

    @unittest.skip("reference URLs changed, checksums now invalid.")
    def test_fetch_bagit_archive_to_folder(self):
        history_id, library, destination = self._setup_fetch_to_folder("bagit_archive")
        example_bag_path = self.test_data_resolver.get_filename("example-bag.zip")
        targets = [
            {
                "destination": destination,
                "items_from": "bagit_archive",
                "src": "files",
            }
        ]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
            "__files": {"files_0|file_data": open(example_bag_path)},
        }
        self.dataset_populator.fetch(payload)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/README.txt")
        assert dataset["file_size"] == 66, dataset

        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/bdbag-profile.json")
        assert dataset["file_size"] == 723, dataset

    def _setup_fetch_to_folder(self, test_name):
        return self.library_populator.setup_fetch_to_folder(test_name)

    @requires_new_library
    def test_create_dataset_in_folder(self):
        library = self.library_populator.new_private_library("ForCreateDatasets")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]["id"]
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content="1 2 3")["id"]
        payload = {"from_hda_id": hda_id}
        create_response = self._post(f"folders/{folder_id}/contents", payload, json=True)
        self._assert_status_code_is(create_response, 200)
        self._assert_has_keys(create_response.json(), "name", "id")

    @requires_new_library
    def test_create_dataset_in_subfolder(self):
        library = self.library_populator.new_private_library("ForCreateDatasets")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]["id"]
        subfolder_response = self._create_subfolder(folder_id)
        self._assert_status_code_is(folder_response, 200)
        print(subfolder_response.json())
        subfolder_id = subfolder_response.json()["id"]
        history_id = self.dataset_populator.new_history()
        expected_dataset_name = "test_dataset_in_subfolder"
        hda_id = self.dataset_populator.new_dataset(history_id, name=expected_dataset_name, content="1 2 3 sub")["id"]
        payload = {"from_hda_id": hda_id}
        create_response = self._post(f"folders/{subfolder_id}/contents", payload, json=True)
        self._assert_status_code_is(create_response, 200)
        self._assert_has_keys(create_response.json(), "name", "id")

        folder_response = self.galaxy_interactor.get(f"folders/{subfolder_id}/contents")
        self._assert_status_code_is(folder_response, 200)
        folder_contents = folder_response.json()["folder_contents"]
        assert len(folder_contents) == 1
        assert folder_contents[0]["name"] == expected_dataset_name

    def _patch_library_dataset(self, library_dataset_id, data):
        create_response = self._patch(f"libraries/datasets/{library_dataset_id}", data=data, json=True)
        self._assert_status_code_is(create_response, 200)
        ld = create_response.json()
        library_id = ld["parent_library_id"]
        return self.library_populator.wait_on_library_dataset(library_id, ld["id"])

    @requires_new_library
    def test_update_dataset_in_folder(self):
        ld = self._create_dataset_in_folder_in_library("ForUpdateDataset", content=">seq\nATGC", wait=True).json()
        data = {
            "name": "updated_name",
            "file_ext": "fasta",
            "misc_info": "updated_info",
            "message": "update message",
        }
        ld_updated = self._patch_library_dataset(ld["id"], data)
        for key, value in data.items():
            assert ld_updated[key] == value

    @requires_new_library
    def test_update_dataset_tags(self):
        ld = self._create_dataset_in_folder_in_library("ForTagtestDataset", wait=True).json()
        data = {"tags": ["#Lancelot", "name:Holy Grail", "blue"]}
        ld_updated = self._patch_library_dataset(ld["id"], data)
        self._assert_has_keys(ld_updated, "tags")
        assert ld_updated["tags"] == ["name:Lancelot", "name:HolyGrail", "blue"]

    @requires_new_library
    def test_invalid_update_dataset_in_folder(self):
        ld = self._create_dataset_in_folder_in_library("ForInvalidUpdateDataset", wait=True).json()
        data = {"file_ext": "nonexisting_type"}
        create_response = self._patch(f"libraries/datasets/{ld['id']}", data=data, json=True)
        self._assert_status_code_is(create_response, 400)
        assert "This Galaxy does not recognize the datatype of:" in create_response.json()["err_msg"]

    @requires_new_library
    def test_detect_datatype_of_dataset_in_folder(self):
        ld = self._create_dataset_in_folder_in_library("ForDetectDataset", wait=True).json()
        data = {"file_ext": "data"}
        ld_updated = self._patch_library_dataset(ld["id"], data)
        self._assert_has_keys(ld_updated, "file_ext")
        assert ld_updated["file_ext"] == "data"
        data = {"file_ext": "auto"}
        ld_updated = self._patch_library_dataset(ld["id"], data)
        self._assert_has_keys(ld_updated, "file_ext")
        assert ld_updated["file_ext"] == "txt"

    @requires_new_library
    def test_ldda_collection_import_to_history(self):
        self._import_to_history(visible=True)

    @requires_new_library
    def test_ldda_collection_import_to_history_hide_source(self):
        self._import_to_history(visible=False)

    @requires_new_library
    def test_import_paired_collection(self):
        ld = self._create_dataset_in_folder_in_library("ForHistoryImport").json()
        history_id = self.dataset_populator.new_history()
        url = f"histories/{history_id}/contents"
        collection_name = "Paired-end data (from library)"
        payload = {
            "name": collection_name,
            "collection_type": "list:paired",
            "type": "dataset_collection",
            "element_identifiers": [
                {
                    "src": "new_collection",
                    "name": "pair1",
                    "collection_type": "paired",
                    "element_identifiers": [
                        {"name": "forward", "src": "ldda", "id": ld["id"]},
                        {"name": "reverse", "src": "ldda", "id": ld["id"]},
                    ],
                }
            ],
        }
        new_collection = self._post(url, payload, json=True).json()
        assert new_collection["name"] == collection_name
        pair = new_collection["elements"][0]
        assert pair["element_identifier"] == "pair1"
        assert pair["object"]["elements"][0]["object"]["history_id"] == history_id

    def _import_to_history(self, visible=True):
        ld = self._create_dataset_in_folder_in_library("ForHistoryImport").json()
        history_id = self.dataset_populator.new_history()
        url = f"histories/{history_id}/contents"
        collection_name = "new_collection_name"
        element_identifer = "new_element_identifier"
        payload = {
            "collection_type": "list",
            "history_content_type": "dataset_collection",
            "model_class": "HistoryDatasetCollectionAssociation",
            "history_id": history_id,
            "name": collection_name,
            "hide_source_items": not visible,
            "element_identifiers": [{"id": ld["id"], "name": element_identifer, "src": "ldda"}],
            "type": "dataset_collection",
            "elements": [],
        }
        new_collection = self._post(url, payload, json=True).json()
        assert new_collection["name"] == collection_name
        assert new_collection["element_count"] == 1
        element = new_collection["elements"][0]
        assert element["element_identifier"] == element_identifer
        assert element["object"]["visible"] == visible

    @requires_new_library
    def test_create_datasets_in_library_from_collection(self):
        library = self.library_populator.new_private_library("ForCreateDatasetsFromCollection")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]["id"]
        history_id = self.dataset_populator.new_history()
        hdca_id = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["xxx", "yyy"], direct_upload=True, wait=True
        ).json()["outputs"][0]["id"]
        payload = {"from_hdca_id": hdca_id, "create_type": "file", "folder_id": folder_id}
        create_response = self._post(f"libraries/{library['id']}/contents", payload, json=True)
        self._assert_status_code_is(create_response, 200)

    @requires_new_library
    def test_create_datasets_in_folder_from_collection(self):
        library = self.library_populator.new_private_library("ForCreateDatasetsFromCollection")
        history_id = self.dataset_populator.new_history()
        hdca_id = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["xxx", "yyy"], direct_upload=True, wait=True
        ).json()["outputs"][0]["id"]
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]["id"]
        payload = {"from_hdca_id": hdca_id}
        create_response = self._post(f"folders/{folder_id}/contents", payload, json=True)
        self._assert_status_code_is(create_response, 200)
        assert len(create_response.json()) == 2
        # Also test that anything different from a flat dataset collection list
        # is refused
        hdca_pair_id = self.dataset_collection_populator.create_list_of_pairs_in_history(history_id, wait=True).json()[
            "outputs"
        ][0]["id"]
        payload = {"from_hdca_id": hdca_pair_id}
        create_response = self._post(f"folders/{folder_id}/contents", payload, json=True)
        self._assert_status_code_is(create_response, 501)
        assert (
            create_response.json()["err_msg"]
            == "Cannot add nested collections to library. Please flatten your collection first."
        )

    def _create_folder(self, library):
        create_data = dict(
            folder_id=library["root_folder_id"],
            create_type="folder",
            name="New Folder",
        )
        return self._post(f"libraries/{library['id']}/contents", data=create_data, json=True)

    def _create_subfolder(self, containing_folder_id):
        create_data = dict(
            description="new subfolder desc",
            name="New Subfolder",
        )
        return self._post(f"folders/{containing_folder_id}", data=create_data, json=True)

    def _create_dataset_in_folder_in_library(self, library_name, content="1 2 3", wait=False):
        library = self.library_populator.new_private_library(library_name)
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]["id"]
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content=content, wait=wait)["id"]
        payload = {"from_hda_id": hda_id, "create_type": "file", "folder_id": folder_id}
        ld = self._post(f"libraries/{library['id']}/contents", payload, json=True)
        ld.raise_for_status()
        return ld

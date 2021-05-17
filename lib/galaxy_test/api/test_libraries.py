import json
import time
import unittest

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    LibraryPopulator,
)
from ._framework import ApiTestCase

FILE_URL = 'https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed'
FILE_MD5 = "37b59762b59fff860460522d271bc111"


class LibrariesApiTestCase(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

    def test_create(self):
        data = dict(name="CreateTestLibrary")
        create_response = self._post("libraries", data=data, admin=True, json=True)
        self._assert_status_code_is(create_response, 200)
        library = create_response.json()
        self._assert_has_keys(library, "name")
        assert library["name"] == "CreateTestLibrary"

    def test_delete(self):
        library = self.library_populator.new_library("DeleteTestLibrary")
        create_response = self._delete(f"libraries/{library['id']}", admin=True)
        self._assert_status_code_is(create_response, 200)
        library = create_response.json()
        self._assert_has_keys(library, "deleted")
        assert library["deleted"] is True
        # Test undeleting
        data = dict(undelete=True)
        create_response = self._delete(f"libraries/{library['id']}", data=data, admin=True)
        library = create_response.json()
        self._assert_status_code_is(create_response, 200)
        assert library["deleted"] is False

    def test_nonadmin(self):
        # Anons can't create libs
        data = dict(name="CreateTestLibrary")
        create_response = self._post("libraries", data=data, admin=False, anon=True, json=True)
        self._assert_status_code_is(create_response, 403)
        # Anons can't delete libs
        library = self.library_populator.new_library("AnonDeleteTestLibrary")
        create_response = self._delete(f"libraries/{library['id']}", admin=False, anon=True)
        self._assert_status_code_is(create_response, 403)
        # Anons can't update libs
        data = dict(name="ChangedName", description="ChangedDescription", synopsis='ChangedSynopsis')
        create_response = self._patch(f"libraries/{library['id']}", data=data, admin=False, anon=True)
        self._assert_status_code_is(create_response, 403)

    def test_update(self):
        library = self.library_populator.new_library("UpdateTestLibrary")
        data = dict(name='ChangedName', description='ChangedDescription', synopsis='ChangedSynopsis')
        create_response = self._patch(f"libraries/{library['id']}", data=data, admin=True)
        self._assert_status_code_is(create_response, 200)
        library = create_response.json()
        self._assert_has_keys(library, 'name', 'description', 'synopsis')
        assert library['name'] == 'ChangedName'
        assert library['description'] == 'ChangedDescription'
        assert library['synopsis'] == 'ChangedSynopsis'

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

    def test_create_dataset_denied(self):
        library = self.library_populator.new_private_library("ForCreateDatasets")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]['id']
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content="1 2 3")['id']
        with self._different_user():
            payload = {'from_hda_id': hda_id}
            create_response = self._post(f"folders/{folder_id}/contents", payload)
            self._assert_status_code_is(create_response, 403)

    def test_show_private_dataset_permissions(self):
        library, library_dataset = self.library_populator.new_library_dataset_in_private_library("ForCreateDatasets", wait=True)
        with self._different_user():
            response = self.library_populator.show_ldda(library["id"], library_dataset["id"])
            # TODO: this should really be 403 and a proper JSON exception.
            self._assert_status_code_is(response, 400)

    def test_create_dataset(self):
        library, library_dataset = self.library_populator.new_library_dataset_in_private_library("ForCreateDatasets", wait=True)
        self._assert_has_keys(library_dataset, "peek", "data_type")
        assert library_dataset["peek"].find("create_test") >= 0
        assert library_dataset["file_ext"] == "txt", library_dataset["file_ext"]

    def test_fetch_upload_to_folder(self):
        history_id, library, destination = self._setup_fetch_to_folder("flat_zip")
        items = [{"src": "files", "dbkey": "hg19", "info": "my cool bed", "created_from_basename": "4.bed"}]
        targets = [{
            "destination": destination,
            "items": items
        }]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": json.dumps(targets),
            "__files": {"files_0|file_data": open(self.test_data_resolver.get_filename("4.bed"))},
        }
        self.dataset_populator.fetch(payload)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset
        assert dataset["genome_build"] == "hg19", dataset
        assert dataset["misc_info"] == "my cool bed", dataset
        assert dataset["file_ext"] == "bed", dataset
        assert dataset["created_from_basename"] == "4.bed"

    def test_fetch_zip_to_folder(self):
        history_id, library, destination = self._setup_fetch_to_folder("flat_zip")
        bed_test_data_path = self.test_data_resolver.get_filename("4.bed.zip")
        targets = [{
            "destination": destination,
            "items_from": "archive", "src": "files",
        }]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": json.dumps(targets),
            "__files": {"files_0|file_data": open(bed_test_data_path, 'rb')}
        }
        self.dataset_populator.fetch(payload)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset

    def test_fetch_single_url_to_folder(self):
        library, response = self._fetch_single_url_to_folder()
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset

    def test_fetch_single_url_with_invalid_datatype(self):
        _, response = self._fetch_single_url_to_folder('xxx', assert_ok=False)
        self._assert_status_code_is(response, 400)
        assert response.json()['err_msg'] == "Requested extension 'xxx' unknown, cannot upload dataset."

    def _fetch_single_url_to_folder(self, file_type='auto', assert_ok=True):
        history_id, library, destination = self._setup_fetch_to_folder("single_url")
        items = [{
            "src": "url",
            "url": FILE_URL,
            "MD5": FILE_MD5,
            "ext": file_type,
        }]
        targets = [{
            "destination": destination,
            "items": items,
        }]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": json.dumps(targets),
            "validate_hashes": True
        }
        return library, self.dataset_populator.fetch(payload, assert_ok=assert_ok)

    def test_legacy_upload_unknown_datatype(self):
        library = self.library_populator.new_private_library("ForLegacyUpload")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]['id']
        payload = {
            'folder_id': folder_id,
            'create_type': 'file',
            'file_type': 'xxx',
            'upload_option': 'upload_file',
            'files_0|url_paste': FILE_URL,
        }
        create_response = self._post(f"libraries/{library['id']}/contents", payload)
        self._assert_status_code_is(create_response, 400)
        assert create_response.json() == "Requested extension 'xxx' unknown, cannot upload dataset."

    def test_fetch_failed_validation(self):
        # Exception handling is really rough here - we should be creating a dataset in error instead
        # of just failing the job like this.
        history_id, library, destination = self._setup_fetch_to_folder("single_url")
        items = [{
            "src": "url",
            "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
            "MD5": "37b59762b59fff860460522d271bc112",
            "name": "4.bed",
        }]
        targets = [{
            "destination": destination,
            "items": items,
        }]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": json.dumps(targets),
            "validate_hashes": True
        }
        tool_response = self.dataset_populator.fetch(payload, assert_ok=False)
        job = self.dataset_populator.check_run(tool_response)
        self.dataset_populator.wait_for_job(job["id"])

        job = tool_response.json()["jobs"][0]
        details = self.dataset_populator.get_job_details(job["id"]).json()
        assert details["state"] == "ok", details

        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["state"] == "error", dataset

    def test_fetch_url_archive_to_folder(self):
        history_id, library, destination = self._setup_fetch_to_folder("single_url")
        targets = [{
            "destination": destination,
            "items_from": "archive",
            "src": "url",
            "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed.zip",
        }]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": json.dumps(targets),
        }
        self.dataset_populator.fetch(payload)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset

    @unittest.skip("reference URLs changed, checksums now invalid.")
    def test_fetch_bagit_archive_to_folder(self):
        history_id, library, destination = self._setup_fetch_to_folder("bagit_archive")
        example_bag_path = self.test_data_resolver.get_filename("example-bag.zip")
        targets = [{
            "destination": destination,
            "items_from": "bagit_archive", "src": "files",
        }]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": json.dumps(targets),
            "__files": {"files_0|file_data": open(example_bag_path)},
        }
        self.dataset_populator.fetch(payload)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/README.txt")
        assert dataset["file_size"] == 66, dataset

        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/bdbag-profile.json")
        assert dataset["file_size"] == 723, dataset

    def _setup_fetch_to_folder(self, test_name):
        return self.library_populator.setup_fetch_to_folder(test_name)

    def test_create_dataset_in_folder(self):
        library = self.library_populator.new_private_library("ForCreateDatasets")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]['id']
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content="1 2 3")['id']
        payload = {'from_hda_id': hda_id}
        create_response = self._post(f"folders/{folder_id}/contents", payload)
        self._assert_status_code_is(create_response, 200)
        self._assert_has_keys(create_response.json(), "name", "id")

    def test_create_dataset_in_subfolder(self):
        library = self.library_populator.new_private_library("ForCreateDatasets")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]['id']
        subfolder_response = self._create_subfolder(folder_id)
        self._assert_status_code_is(folder_response, 200)
        print(subfolder_response.json())
        subfolder_id = subfolder_response.json()['id']
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content="1 2 3 sub")['id']
        payload = {'from_hda_id': hda_id}
        create_response = self._post(f"folders/{subfolder_id}/contents", payload)
        self._assert_status_code_is(create_response, 200)
        self._assert_has_keys(create_response.json(), "name", "id")
        dataset_update_time = create_response.json()['update_time']
        container_fetch_response = self.galaxy_interactor.get(f"folders/{folder_id}/contents")
        container_update_time = container_fetch_response.json()['folder_contents'][0]['update_time']
        assert dataset_update_time == container_update_time, container_fetch_response

    def test_update_dataset_in_folder(self):
        ld = self._create_dataset_in_folder_in_library("ForUpdateDataset", wait=True)
        data = {'name': 'updated_name', 'file_ext': 'fastq', 'misc_info': 'updated_info', 'genome_build': 'updated_genome_build'}
        create_response = self._patch(f"libraries/datasets/{ld.json()['id']}", data=data)
        self._assert_status_code_is(create_response, 200)
        self._assert_has_keys(create_response.json(), "name", "file_ext", "misc_info", "genome_build")

    def test_update_dataset_tags(self):
        ld = self._create_dataset_in_folder_in_library("ForTagtestDataset")
        data = {"tags": ["#Lancelot", "name:Holy Grail", "blue"]}
        create_response = self._patch(f"libraries/datasets/{ld.json()['id']}", data=data)
        self._assert_status_code_is(create_response, 200)
        self._assert_has_keys(create_response.json(), "tags")
        assert create_response.json()["tags"] == "name:Lancelot, name:HolyGrail, blue"

    def test_invalid_update_dataset_in_folder(self):
        ld = self._create_dataset_in_folder_in_library("ForInvalidUpdateDataset")
        data = {'file_ext': 'nonexisting_type'}
        create_response = self._patch(f"libraries/datasets/{ld.json()['id']}", data=data)
        self._assert_status_code_is(create_response, 400)
        assert 'This Galaxy does not recognize the datatype of:' in create_response.json()['err_msg']

    def test_detect_datatype_of_dataset_in_folder(self):
        ld = self._create_dataset_in_folder_in_library("ForDetectDataset")
        # Wait for metadata job to finish.
        time.sleep(2)
        data = {'file_ext': 'data'}
        create_response = self._patch(f"libraries/datasets/{ld.json()['id']}", data=data)
        self._assert_status_code_is(create_response, 200)
        self._assert_has_keys(create_response.json(), "file_ext")
        assert create_response.json()["file_ext"] == "data"
        # Wait for metadata job to finish.
        time.sleep(2)
        data = {'file_ext': 'auto'}
        create_response = self._patch(f"libraries/datasets/{ld.json()['id']}", data=data)
        self._assert_status_code_is(create_response, 200)
        self._assert_has_keys(create_response.json(), "file_ext")
        assert create_response.json()["file_ext"] == "txt"

    def test_ldda_collection_import_to_history(self):
        self._import_to_history(visible=True)

    def test_ldda_collection_import_to_history_hide_source(self):
        self._import_to_history(visible=False)

    def test_import_paired_collection(self):
        ld = self._create_dataset_in_folder_in_library("ForHistoryImport").json()
        history_id = self.dataset_populator.new_history()
        url = f"histories/{history_id}/contents"
        collection_name = 'Paired-end data (from library)'
        payload = {
            'name': collection_name,
            'collection_type': 'list:paired',
            "type": "dataset_collection",
            'element_identifiers': json.dumps([
                {
                    'src': 'new_collection',
                    'name': 'pair1',
                    'collection_type': 'paired',
                    'element_identifiers': [{'name': 'forward', 'src': 'ldda', 'id': ld['id']},
                                            {'name': 'reverse', 'src': 'ldda', 'id': ld['id']}]
                }
            ])
        }
        new_collection = self._post(url, payload).json()
        assert new_collection['name'] == collection_name
        pair = new_collection['elements'][0]
        assert pair['element_identifier'] == 'pair1'
        assert pair['object']['elements'][0]['object']['history_id'] == history_id

    def _import_to_history(self, visible=True):
        ld = self._create_dataset_in_folder_in_library("ForHistoryImport").json()
        history_id = self.dataset_populator.new_history()
        url = f"histories/{history_id}/contents"
        collection_name = 'new_collection_name'
        element_identifer = 'new_element_identifier'
        payload = {
            "collection_type": "list",
            "history_content_type": "dataset_collection",
            "model_class": "HistoryDatasetCollectionAssociation",
            "history_id": history_id,
            "name": collection_name,
            "hide_source_items": not visible,
            "element_identifiers": json.dumps([{
                "id": ld['id'],
                "name": element_identifer,
                "src": "ldda"}]),
            "type": "dataset_collection",
            "elements": []
        }
        new_collection = self._post(url, payload).json()
        assert new_collection['name'] == collection_name
        assert new_collection['element_count'] == 1
        element = new_collection['elements'][0]
        assert element['element_identifier'] == element_identifer
        assert element['object']['visible'] == visible

    def test_create_datasets_in_library_from_collection(self):
        library = self.library_populator.new_private_library("ForCreateDatasetsFromCollection")
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]['id']
        history_id = self.dataset_populator.new_history()
        hdca_id = self.dataset_collection_populator.create_list_in_history(history_id, contents=["xxx", "yyy"], direct_upload=True).json()["outputs"][0]["id"]
        payload = {'from_hdca_id': hdca_id, 'create_type': 'file', 'folder_id': folder_id}
        create_response = self._post(f"libraries/{library['id']}/contents", payload)
        self._assert_status_code_is(create_response, 200)

    def test_create_datasets_in_folder_from_collection(self):
        library = self.library_populator.new_private_library("ForCreateDatasetsFromCollection")
        history_id = self.dataset_populator.new_history()
        hdca_id = self.dataset_collection_populator.create_list_in_history(history_id, contents=["xxx", "yyy"], direct_upload=True).json()["outputs"][0]["id"]
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]['id']
        payload = {'from_hdca_id': hdca_id}
        create_response = self._post(f"folders/{folder_id}/contents", payload)
        self._assert_status_code_is(create_response, 200)
        assert len(create_response.json()) == 2
        # Also test that anything different from a flat dataset collection list
        # is refused
        hdca_pair_id = self.dataset_collection_populator.create_list_of_pairs_in_history(history_id).json()["outputs"][0]['id']
        payload = {'from_hdca_id': hdca_pair_id}
        create_response = self._post(f"folders/{folder_id}/contents", payload)
        self._assert_status_code_is(create_response, 501)
        assert create_response.json()['err_msg'] == 'Cannot add nested collections to library. Please flatten your collection first.'

    def _create_folder(self, library):
        create_data = dict(
            folder_id=library["root_folder_id"],
            create_type="folder",
            name="New Folder",
        )
        return self._post(f"libraries/{library['id']}/contents", data=create_data)

    def _create_subfolder(self, containing_folder_id):
        create_data = dict(
            description="new subfolder desc",
            name="New Subfolder",
        )
        return self._post(f"folders/{containing_folder_id}", data=create_data)

    def _create_dataset_in_folder_in_library(self, library_name, wait=False):
        library = self.library_populator.new_private_library(library_name)
        folder_response = self._create_folder(library)
        self._assert_status_code_is(folder_response, 200)
        folder_id = folder_response.json()[0]['id']
        history_id = self.dataset_populator.new_history()
        hda_id = self.dataset_populator.new_dataset(history_id, content="1 2 3", wait=wait)['id']
        payload = {'from_hda_id': hda_id, 'create_type': 'file', 'folder_id': folder_id}
        ld = self._post(f"libraries/{folder_id}/contents", payload)
        return ld

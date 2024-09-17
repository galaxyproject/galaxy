import zipfile
from io import BytesIO
from typing import List

from galaxy.util.unittest_utils import skip_if_github_down
from galaxy_test.base.api_asserts import assert_object_id_error
from galaxy_test.base.decorators import requires_new_user
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from ._framework import ApiTestCase


class TestDatasetCollectionsApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_create_pair_from_history(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            payload = self.dataset_collection_populator.create_pair_payload(
                history_id,
                instance_type="history",
            )
            create_response = self.dataset_populator.fetch(payload, wait=True)
            dataset_collection = self._check_create_response(create_response)
            returned_datasets = dataset_collection["elements"]
            assert len(returned_datasets) == 2, dataset_collection

    def test_create_list_from_history(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            element_identifiers = self.dataset_collection_populator.list_identifiers(history_id)

            payload = dict(
                instance_type="history",
                history_id=history_id,
                element_identifiers=element_identifiers,
                collection_type="list",
            )

            create_response = self._post("dataset_collections", payload, json=True)
            dataset_collection = self._check_create_response(create_response)
            returned_datasets = dataset_collection["elements"]
            assert len(returned_datasets) == 3, dataset_collection

    def test_create_list_of_existing_pairs(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            pair_payload = self.dataset_collection_populator.create_pair_payload(
                history_id,
                instance_type="history",
            )
            pair_create_response = self._post("tools/fetch", pair_payload, json=True)
            dataset_collection = self._check_create_response(pair_create_response)
            hdca_id = dataset_collection["id"]

            element_identifiers = [dict(name="test1", src="hdca", id=hdca_id)]

            payload = dict(
                instance_type="history",
                history_id=history_id,
                element_identifiers=element_identifiers,
                collection_type="list",
            )
            create_response = self._post("dataset_collections", payload, json=True)
            dataset_collection = self._check_create_response(create_response)
            returned_collections = dataset_collection["elements"]
            assert len(returned_collections) == 1, dataset_collection

    def test_create_list_of_new_pairs(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            identifiers = self.dataset_collection_populator.nested_collection_identifiers(history_id, "list:paired")
            payload = dict(
                collection_type="list:paired",
                instance_type="history",
                history_id=history_id,
                name="a nested collection",
                element_identifiers=identifiers,
            )
            create_response = self._post("dataset_collections", payload, json=True)
            dataset_collection = self._check_create_response(create_response)
            assert dataset_collection["collection_type"] == "list:paired"
            assert dataset_collection["name"] == "a nested collection"
            returned_collections = dataset_collection["elements"]
            assert len(returned_collections) == 1, dataset_collection
            pair_1_element = returned_collections[0]
            self._assert_has_keys(pair_1_element, "element_identifier", "element_index", "object")
            assert pair_1_element["element_identifier"] == "test_level_1", pair_1_element
            assert pair_1_element["element_index"] == 0, pair_1_element
            pair_1_object = pair_1_element["object"]
            self._assert_has_keys(pair_1_object, "collection_type", "elements", "element_count")
            assert pair_1_object["collection_type"] == "paired"
            assert pair_1_object["populated"] is True
            pair_elements = pair_1_object["elements"]
            assert len(pair_elements) == 2
            pair_1_element_1 = pair_elements[0]
            assert pair_1_element_1["element_index"] == 0

    def test_list_download(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, direct_upload=True
            ).json()
            dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
            returned_dce = dataset_collection["elements"]
            assert len(returned_dce) == 3, dataset_collection
            create_response = self._download_dataset_collection(history_id=history_id, hdca_id=dataset_collection["id"])
            self._assert_status_code_is(create_response, 200)
            archive = zipfile.ZipFile(BytesIO(create_response.content))
            namelist = archive.namelist()
            assert len(namelist) == 3, f"Expected 3 elements in [{namelist}]"
            collection_name = dataset_collection["name"]
            for element, zip_path in zip(returned_dce, namelist):
                assert f"{collection_name}/{element['element_identifier']}.{element['object']['file_ext']}" == zip_path

    def test_pair_download(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            fetch_response = self.dataset_collection_populator.create_pair_in_history(
                history_id, direct_upload=True
            ).json()
            dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
            returned_dce = dataset_collection["elements"]
            assert len(returned_dce) == 2, dataset_collection
            hdca_id = dataset_collection["id"]
            create_response = self._download_dataset_collection(history_id=history_id, hdca_id=hdca_id)
            self._assert_status_code_is(create_response, 200)
            archive = zipfile.ZipFile(BytesIO(create_response.content))
            namelist = archive.namelist()
            assert len(namelist) == 2, f"Expected 2 elements in [{namelist}]"
            collection_name = dataset_collection["name"]
            for element, zip_path in zip(returned_dce, namelist):
                assert f"{collection_name}/{element['element_identifier']}.{element['object']['file_ext']}" == zip_path

    def test_list_pair_download(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            fetch_response = self.dataset_collection_populator.create_list_of_pairs_in_history(history_id).json()
            dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
            returned_dce = dataset_collection["elements"]
            assert len(returned_dce) == 1, dataset_collection
            list_collection_name = dataset_collection["name"]
            pair = returned_dce[0]
            create_response = self._download_dataset_collection(history_id=history_id, hdca_id=dataset_collection["id"])
            self._assert_status_code_is(create_response, 200)
            archive = zipfile.ZipFile(BytesIO(create_response.content))
            namelist = archive.namelist()
            assert len(namelist) == 2, f"Expected 2 elements in [{namelist}]"
            pair_collection_name = pair["element_identifier"]
            for element, zip_path in zip(pair["object"]["elements"], namelist):
                assert (
                    f"{list_collection_name}/{pair_collection_name}/{element['element_identifier']}.{element['object']['file_ext']}"
                    == zip_path
                )

    def test_list_list_download(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            dataset_collection = self.dataset_collection_populator.create_list_of_list_in_history(
                history_id, wait=True
            ).json()
            returned_dce = dataset_collection["elements"]
            assert len(returned_dce) == 1, dataset_collection
            create_response = self._download_dataset_collection(history_id=history_id, hdca_id=dataset_collection["id"])
            self._assert_status_code_is(create_response, 200)
            archive = zipfile.ZipFile(BytesIO(create_response.content))
            namelist = archive.namelist()
            assert len(namelist) == 3, f"Expected 3 elements in [{namelist}]"

    def test_list_list_list_download(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            dataset_collection = self.dataset_collection_populator.create_list_of_list_in_history(
                history_id,
                collection_type="list:list:list",
                wait=True,
            ).json()
            returned_dce = dataset_collection["elements"]
            assert len(returned_dce) == 1, dataset_collection
            create_response = self._download_dataset_collection(history_id=history_id, hdca_id=dataset_collection["id"])
            self._assert_status_code_is(create_response, 200)
            archive = zipfile.ZipFile(BytesIO(create_response.content))
            namelist = archive.namelist()
            assert len(namelist) == 3, f"Expected 3 elements in [{namelist}]"

    def test_download_non_english_characters(self):
        with self.dataset_populator.test_history() as history_id:
            name = "دیتاست"
            payload = self.dataset_collection_populator.create_list_payload(history_id, name=name)
            hdca_id = self.dataset_populator.fetch(payload, wait=True).json()["outputs"][0]["id"]
            create_response = self._download_dataset_collection(history_id=history_id, hdca_id=hdca_id)
            self._assert_status_code_is(create_response, 200)

    @requires_new_user
    def test_hda_security(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            element_identifiers = self.dataset_collection_populator.pair_identifiers(history_id, wait=True)
            self.dataset_populator.make_private(history_id, element_identifiers[0]["id"])
            with self._different_user():
                history_id = self.dataset_populator.new_history()
                payload = dict(
                    instance_type="history",
                    history_id=history_id,
                    element_identifiers=element_identifiers,
                    collection_type="paired",
                )
                create_response = self._post("dataset_collections", payload, json=True)
                self._assert_status_code_is(create_response, 403)

    def test_dataset_collection_element_security(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            dataset_collection = self.dataset_collection_populator.create_list_of_list_in_history(
                history_id,
                collection_type="list:list:list",
                wait=True,
            ).json()
            first_element = dataset_collection["elements"][0]
            assert first_element["model_class"] == "DatasetCollectionElement"
            assert first_element["element_type"] == "dataset_collection"
            first_element_url = f"/api/dataset_collection_element/{first_element['id']}"
            # Make one dataset private to check that access permissions are respected
            first_dataset_element = first_element["object"]["elements"][0]["object"]["elements"][0]
            self.dataset_populator.make_private(history_id, first_dataset_element["object"]["id"])
            with self._different_user():
                assert self._get(first_element_url).status_code == 403
            collection_dce_response = self._get(first_element_url)
            collection_dce_response.raise_for_status()
            collection_dce = collection_dce_response.json()
            assert collection_dce["model_class"] == "DatasetCollectionElement"
            assert collection_dce["element_type"] == "dataset_collection"
            first_dataset_element = first_element["object"]["elements"][0]["object"]["elements"][0]
            assert first_dataset_element["model_class"] == "DatasetCollectionElement"
            assert first_dataset_element["element_type"] == "hda"
            first_dataset_element_url = f"/api/dataset_collection_element/{first_dataset_element['id']}"
            with self._different_user():
                assert self._get(first_dataset_element_url).status_code == 403
            dataset_dce_response = self._get(first_dataset_element_url)
            dataset_dce_response.raise_for_status()
            dataset_dce = dataset_dce_response.json()
            assert dataset_dce["model_class"] == "DatasetCollectionElement"
            assert dataset_dce["element_type"] == "hda"
            assert dataset_dce["object"]["model_class"] == "HistoryDatasetAssociation"

    def test_enforces_unique_names(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            element_identifiers = self.dataset_collection_populator.list_identifiers(history_id)
            element_identifiers[2]["name"] = element_identifiers[0]["name"]
            payload = dict(
                instance_type="history",
                history_id=history_id,
                element_identifiers=element_identifiers,
                collection_type="list",
            )

            create_response = self._post("dataset_collections", payload, json=True)
            self._assert_status_code_is(create_response, 400)

    def test_upload_collection(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            elements = [
                {
                    "src": "files",
                    "dbkey": "hg19",
                    "info": "my cool bed",
                    "tags": ["name:data1", "group:condition:treated", "machine:illumina"],
                }
            ]
            targets = [
                {
                    "destination": {"type": "hdca"},
                    "elements": elements,
                    "collection_type": "list",
                    "name": "Test upload",
                    "tags": ["name:collection1"],
                }
            ]
            payload = {
                "history_id": history_id,
                "targets": targets,
                "__files": {"files_0|file_data": open(self.test_data_resolver.get_filename("4.bed"))},
            }
            self.dataset_populator.fetch(payload)
            hdca = self._assert_one_collection_created_in_history(history_id)
            assert hdca["name"] == "Test upload"
            hdca_tags = hdca["tags"]
            assert len(hdca_tags) == 1
            assert "name:collection1" in hdca_tags
            assert len(hdca["elements"]) == 1, hdca
            element0 = hdca["elements"][0]
            assert element0["element_identifier"] == "4.bed"
            dataset0 = element0["object"]
            assert dataset0["file_size"] == 61
            dataset_tags = dataset0["tags"]
            assert len(dataset_tags) == 3, dataset0

    def test_upload_nested(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            elements = [{"name": "samp1", "elements": [{"src": "files", "dbkey": "hg19", "info": "my cool bed"}]}]
            targets = [
                {
                    "destination": {"type": "hdca"},
                    "elements": elements,
                    "collection_type": "list:list",
                    "name": "Test upload",
                }
            ]
            payload = {
                "history_id": history_id,
                "targets": targets,
                "__files": {"files_0|file_data": open(self.test_data_resolver.get_filename("4.bed"))},
            }
            self.dataset_populator.fetch(payload)
            hdca = self._assert_one_collection_created_in_history(history_id)
            assert hdca["name"] == "Test upload"
            assert len(hdca["elements"]) == 1, hdca
            element0 = hdca["elements"][0]
            assert element0["element_identifier"] == "samp1"

    @skip_if_github_down
    def test_upload_collection_from_url(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            elements = [
                {
                    "src": "url",
                    "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
                    "info": "my cool bed",
                }
            ]
            targets = [
                {
                    "destination": {"type": "hdca"},
                    "elements": elements,
                    "collection_type": "list",
                }
            ]
            payload = {
                "history_id": history_id,
                "targets": targets,
            }
            self.dataset_populator.fetch(payload)
            hdca = self._assert_one_collection_created_in_history(history_id)
            assert len(hdca["elements"]) == 1, hdca
            element0 = hdca["elements"][0]
            assert element0["element_identifier"] == "4.bed"
            assert element0["object"]["file_size"] == 61

    def test_upload_collection_deferred(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            elements = [
                {
                    "src": "url",
                    "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
                    "info": "my cool bed",
                    "deferred": True,
                }
            ]
            targets = [
                {
                    "destination": {"type": "hdca"},
                    "elements": elements,
                    "collection_type": "list",
                }
            ]
            payload = {
                "history_id": history_id,
                "targets": targets,
            }
            self.dataset_populator.fetch(payload)
            hdca = self._assert_one_collection_created_in_history(history_id)
            assert len(hdca["elements"]) == 1, hdca
            element0 = hdca["elements"][0]
            assert element0["element_identifier"] == "4.bed"
            object0 = element0["object"]
            assert object0["state"] == "deferred"

    @skip_if_github_down
    def test_upload_collection_failed_expansion_url(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            targets = [
                {
                    "destination": {"type": "hdca"},
                    "elements_from": "bagit",
                    "collection_type": "list",
                    "src": "url",
                    "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
                }
            ]
            payload = {
                "history_id": history_id,
                "targets": targets,
            }
            self.dataset_populator.fetch(payload, assert_ok=False, wait=True)
            hdca = self._assert_one_collection_created_in_history(history_id)
            assert hdca["populated"] is False
            assert "bagit.txt" in hdca["populated_state_message"], hdca

    def _assert_one_collection_created_in_history(self, history_id: str):
        contents_response = self._get(f"histories/{history_id}/contents/dataset_collections")
        self._assert_status_code_is(contents_response, 200)
        contents = contents_response.json()
        assert len(contents) == 1
        hdca = contents[0]
        assert hdca["history_content_type"] == "dataset_collection"
        hdca_id = hdca["id"]
        collection_response = self._get(f"histories/{history_id}/contents/dataset_collections/{hdca_id}")
        self._assert_status_code_is(collection_response, 200)
        return collection_response.json()

    def _check_create_response(self, create_response):
        self._assert_status_code_is(create_response, 200)
        dataset_collection = create_response.json()
        if "output_collections" in dataset_collection:
            # fetch data response, we'll have to check the final response
            dataset_collection = dataset_collection["output_collections"][0]
            dataset_collection = self._get(f"dataset_collections/{dataset_collection['id']}").json()
        self._assert_has_keys(dataset_collection, "elements", "url", "name", "collection_type", "element_count")
        return dataset_collection

    def _download_dataset_collection(self, history_id: str, hdca_id: str):
        return self._get(f"histories/{history_id}/contents/dataset_collections/{hdca_id}/download")

    @requires_new_user
    def test_collection_contents_security(self, history_id):
        # request contents on an hdca that doesn't belong to user
        hdca, contents_url = self._create_collection_contents_pair(history_id)
        with self._different_user():
            contents_response = self._get(contents_url)
            self._assert_status_code_is(contents_response, 403)

    @requires_new_user
    def test_published_collection_contents_accessible(self, history_id):
        # request contents on an hdca that is in a published history
        hdca, contents_url = self._create_collection_contents_pair(history_id)
        with self._different_user():
            contents_response = self._get(contents_url)
            self._assert_status_code_is(contents_response, 403)
        self.dataset_populator.make_public(history_id)
        with self._different_user():
            contents_response = self._get(contents_url)
            self._assert_status_code_is(contents_response, 200)

    def test_collection_contents_invalid_collection(self, history_id):
        # request an invalid collection from a valid hdca, should get 404
        hdca, contents_url = self._create_collection_contents_pair(history_id)
        response = self._get(contents_url)
        self._assert_status_code_is(response, 200)
        fake_collection_id = "5d7db0757a2eb7ef"
        fake_contents_url = f"/api/dataset_collections/{hdca['id']}/contents/{fake_collection_id}"
        error_response = self._get(fake_contents_url)
        assert_object_id_error(error_response)

    def test_show_dataset_collection(self, history_id):
        fetch_response = self.dataset_collection_populator.create_list_in_history(history_id, direct_upload=True).json()
        dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        returned_dce = dataset_collection["elements"]
        assert len(returned_dce) == 3, dataset_collection
        hdca_id = dataset_collection["id"]
        dataset_collection_url = f"/api/dataset_collections/{hdca_id}"
        dataset_collection = self._get(dataset_collection_url).json()
        assert dataset_collection["id"] == hdca_id
        assert dataset_collection["collection_type"] == "list"

    def test_show_dataset_collection_contents(self, history_id):
        # Get contents_url from history contents, use it to show the first level
        # of collection contents in the created HDCA, then use it again to drill
        # down into the nested collection contents
        hdca = self.dataset_collection_populator.create_list_of_list_in_history(history_id, wait=True).json()
        root_contents_url = self._get_contents_url_for_hdca(history_id, hdca)

        # check root contents for this collection
        root_contents = self._get(root_contents_url).json()
        assert len(root_contents) == len(hdca["elements"])
        self._compare_collection_contents_elements(root_contents, hdca["elements"])

        # drill down, retrieve nested collection contents
        assert "object" in root_contents[0]
        assert "contents_url" in root_contents[0]["object"]
        assert root_contents[0]["object"]["element_count"] == 3
        assert root_contents[0]["object"]["populated"]
        drill_contents_url = root_contents[0]["object"]["contents_url"]
        drill_contents = self._get(drill_contents_url).json()
        assert len(drill_contents) == len(hdca["elements"][0]["object"]["elements"])
        self._compare_collection_contents_elements(drill_contents, hdca["elements"][0]["object"]["elements"])

    def test_collection_contents_limit_offset(self, history_id):
        # check limit/offset params for collection contents endpoint
        hdca, root_contents_url = self._create_collection_contents_pair(history_id)

        # check limit
        limited_contents = self._get(f"{root_contents_url}?limit=1").json()
        assert len(limited_contents) == 1
        assert limited_contents[0]["element_index"] == 0

        # check offset
        offset_contents = self._get(f"{root_contents_url}?offset=1").json()
        assert len(offset_contents) == 1
        assert offset_contents[0]["element_index"] == 1

    def test_collection_contents_empty_root(self, history_id):
        create_response = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=[], wait=True
        ).json()
        hdca = create_response["output_collections"][0]
        assert hdca["elements"] == []
        root_contents_url = hdca["contents_url"]
        response = self._get(root_contents_url)
        response.raise_for_status()
        assert response.json() == []

    def test_get_suitable_converters_single_datatype(self, history_id):
        response = self.dataset_collection_populator.upload_collection(
            history_id,
            "list:paired",
            elements=[
                {
                    "name": "test0",
                    "elements": [
                        {"src": "pasted", "paste_content": "123\n", "name": "forward", "ext": "bed"},
                        {"src": "pasted", "paste_content": "456\n", "name": "reverse", "ext": "bed"},
                    ],
                },
                {
                    "name": "test1",
                    "elements": [
                        {"src": "pasted", "paste_content": "789\n", "name": "forward", "ext": "bed"},
                        {"src": "pasted", "paste_content": "0ab\n", "name": "reverse", "ext": "bed"},
                    ],
                },
            ],
            wait=True,
        )
        self._assert_status_code_is(response, 200)
        hdca_list_id = response.json()["outputs"][0]["id"]
        converters = self._get("dataset_collections/" + hdca_list_id + "/suitable_converters")
        expected = [  # This list is subject to change, but it's unlikely we'll be removing converters
            "CONVERTER_bed_to_fli_0",
            "CONVERTER_bed_gff_or_vcf_to_bigwig_0",
            "CONVERTER_bed_to_gff_0",
            "CONVERTER_interval_to_bgzip_0",
            "tabular_to_csv",
            "CONVERTER_interval_to_bed6_0",
            "CONVERTER_interval_to_bedstrict_0",
            "CONVERTER_interval_to_tabix_0",
            "CONVERTER_interval_to_bed12_0",
        ]
        actual = []
        for converter in converters.json():
            actual.append(converter["tool_id"])
        missing_expected_converters = set(expected) - set(actual)
        assert (
            not missing_expected_converters
        ), f"Expected converter(s) {', '.join(missing_expected_converters)} missing from response"

    def test_get_suitable_converters_different_datatypes_matches(self, history_id):
        response = self.dataset_collection_populator.upload_collection(
            history_id,
            "list:paired",
            elements=[
                {
                    "name": "test0",
                    "elements": [
                        {"src": "pasted", "paste_content": "123\n", "name": "forward", "ext": "bed"},
                        {"src": "pasted", "paste_content": "456\n", "name": "reverse", "ext": "bed"},
                    ],
                },
                {
                    "name": "test1",
                    "elements": [
                        {"src": "pasted", "paste_content": "789\n", "name": "forward", "ext": "tabular"},
                        {"src": "pasted", "paste_content": "0ab\n", "name": "reverse", "ext": "tabular"},
                    ],
                },
            ],
            wait=True,
        )
        self._assert_status_code_is(response, 200)
        hdca_list_id = response.json()["outputs"][0]["id"]
        converters = self._get("dataset_collections/" + hdca_list_id + "/suitable_converters")
        expected = "tabular_to_csv"
        actual = []
        for converter in converters.json():
            actual.append(converter["tool_id"])
        assert expected in actual

    def test_get_suitable_converters_different_datatypes_no_matches(self, history_id):
        response = self.dataset_collection_populator.upload_collection(
            history_id,
            "list:paired",
            elements=[
                {
                    "name": "test0",
                    "elements": [
                        {"src": "pasted", "paste_content": "123\n", "name": "forward", "ext": "bed"},
                        {"src": "pasted", "paste_content": "456\n", "name": "reverse", "ext": "bed"},
                    ],
                },
                {
                    "name": "test1",
                    "elements": [
                        {"src": "pasted", "paste_content": "789\n", "name": "forward", "ext": "fasta"},
                        {"src": "pasted", "paste_content": "0ab\n", "name": "reverse", "ext": "fasta"},
                    ],
                },
            ],
            wait=True,
        )
        self._assert_status_code_is(response, 200)
        hdca_list_id = response.json()["outputs"][0]["id"]
        converters = self._get("dataset_collections/" + hdca_list_id + "/suitable_converters")
        actual: List[str] = []
        for converter in converters.json():
            actual.append(converter["tool_id"])
        assert actual == []

    def test_collection_tools_tag_propagation(self, history_id):
        elements = [{"src": "files", "tags": ["name:element_tag"]}]
        targets = [
            {
                "destination": {"type": "hdca"},
                "elements": elements,
                "collection_type": "list",
                "name": "Test collection",
                "tags": ["name:collection_tag"],
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": targets,
            "__files": {"files_0|file_data": open(self.test_data_resolver.get_filename("4.bed"))},
        }
        hdca_id = self.dataset_populator.fetch(payload).json()["output_collections"][0]["id"]
        inputs = {
            "input": {"batch": False, "src": "hdca", "id": hdca_id},
        }
        payload = self.dataset_populator.run_tool_payload(
            tool_id="__FILTER_FAILED_DATASETS__",
            inputs=inputs,
            history_id=history_id,
            input_format="legacy",
        )
        response = self._post("tools", payload).json()
        self.dataset_populator.wait_for_history(history_id, assert_ok=False)
        output_collection = response["output_collections"][0]
        # collection should not inherit tags from input collection elements, only parent collection
        assert output_collection["tags"] == ["name:collection_tag"]
        element = output_collection["elements"][0]
        # new element hda should have tags copied from old hda
        assert element["object"]["tags"] == ["name:element_tag"]

    def _compare_collection_contents_elements(self, contents_elements, hdca_elements):
        # compare collection api results to existing hdca element contents
        fields = ["element_identifier", "element_index", "element_type", "id", "model_class"]
        for content_element, hdca_element in zip(contents_elements, hdca_elements):
            for f in fields:
                assert content_element[f] == hdca_element[f]

    def _create_collection_contents_pair(self, history_id: str):
        # Create a simple collection, return hdca and contents_url
        payload = self.dataset_collection_populator.create_pair_payload(history_id, instance_type="history")
        create_response = self.dataset_populator.fetch(payload=payload, wait=True)
        hdca = self._check_create_response(create_response)
        root_contents_url = self._get_contents_url_for_hdca(history_id, hdca)
        return hdca, root_contents_url

    def _get_contents_url_for_hdca(self, history_id: str, hdca):
        # look up the history contents using optional serialization key
        history_contents_url = f"histories/{history_id}/contents?v=dev&view=summary&keys=contents_url"
        json = self._get(history_contents_url).json()

        # filter out the collection we just made id = hdca.id
        # make sure the contents_url appears
        def find_hdca(c):
            return c["history_content_type"] == "dataset_collection" and c["id"] == hdca["id"]

        matches = list(filter(find_hdca, json))
        assert len(matches) == 1
        assert "contents_url" in matches[0]

        return matches[0]["contents_url"]

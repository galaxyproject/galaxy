import textwrap
import urllib
import zipfile
from io import BytesIO
from typing import (
    Dict,
    List,
)
from urllib.parse import quote

from galaxy.model.unittest_utils.store_fixtures import (
    deferred_hda_model_store_dict,
    one_hda_model_store_dict,
    TEST_SOURCE_URI,
)
from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.util.unittest_utils import skip_if_github_down
from galaxy_test.base.api_asserts import assert_has_keys
from galaxy_test.base.decorators import (
    requires_admin,
    requires_new_history,
)
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_datatype,
    skip_without_tool,
)
from ._framework import ApiTestCase

COMPOSITE_DATA_FETCH_REQUEST_1 = {
    "src": "composite",
    "ext": "velvet",
    "composite": {
        "items": [
            {"src": "pasted", "paste_content": "sequences content"},
            {"src": "pasted", "paste_content": "roadmaps content"},
            {"src": "pasted", "paste_content": "log content"},
        ]
    },
}


class TestDatasetsApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_index(self):
        index_response = self._get("datasets")
        self._assert_status_code_is(index_response, 200)

    def test_index_using_keys(self, history_id):
        expected_keys = "id"
        self.dataset_populator.new_dataset(history_id)
        index_response = self._get(f"datasets?keys={expected_keys}")
        self._assert_status_code_is(index_response, 200)
        datasets = index_response.json()
        for dataset in datasets:
            assert len(dataset) == 1
            self._assert_has_keys(dataset, "id")

    @requires_new_history
    def test_index_order_by_size(self):
        num_datasets = 3
        history_id = self.dataset_populator.new_history()
        dataset_ids_ordered_by_size_asc = []
        for index in range(num_datasets):
            dataset_content = (index + 1) * "content"
            hda = self.dataset_populator.new_dataset(history_id, content=dataset_content)
            dataset_ids_ordered_by_size_asc.append(hda["id"])
        dataset_ids_ordered_by_size = dataset_ids_ordered_by_size_asc[::-1]
        self.dataset_populator.wait_for_history(history_id)

        self._assert_history_datasets_ordered(
            history_id, order_by="size", expected_ids_order=dataset_ids_ordered_by_size
        )
        self._assert_history_datasets_ordered(
            history_id, order_by="size-asc", expected_ids_order=dataset_ids_ordered_by_size_asc
        )

    def _assert_history_datasets_ordered(self, history_id, order_by: str, expected_ids_order: List[str]):
        datasets_response = self._get(f"histories/{history_id}/contents?v=dev&keys=size&order={order_by}")
        self._assert_status_code_is(datasets_response, 200)
        datasets = datasets_response.json()
        assert len(datasets) == len(expected_ids_order)
        for index, dataset in enumerate(datasets):
            assert dataset["id"] == expected_ids_order[index]

    @requires_new_history
    def test_search_datasets(self):
        with self.dataset_populator.test_history_for(self.test_search_datasets) as history_id:
            hda_id = self.dataset_populator.new_dataset(history_id)["id"]
            payload = {"limit": 1, "offset": 0, "history_id": history_id}
            index_response = self._get("datasets", payload).json()
            assert len(index_response) == 1
            assert index_response[0]["id"] == hda_id
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["1\n2\n3"]
            ).json()
            hdca_id = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)["id"]
            index_payload_1 = {"limit": 3, "offset": 0, "order": "hid", "history_id": history_id}
            index_response = self._get("datasets", index_payload_1).json()
            assert len(index_response) == 3
            assert index_response[0]["hid"] == 3
            assert index_response[1]["hid"] == 2
            assert index_response[2]["hid"] == 1
            assert index_response[2]["history_content_type"] == "dataset"
            assert index_response[2]["id"] == hda_id
            assert index_response[1]["history_content_type"] == "dataset_collection"
            assert index_response[1]["id"] == hdca_id
            index_payload_2 = {"limit": 2, "offset": 0, "q": ["history_content_type"], "qv": ["dataset"]}
            index_response = self._get("datasets", index_payload_2).json()
            assert index_response[1]["id"] == hda_id

    @requires_new_history
    def test_search_by_tag(self):
        with self.dataset_populator.test_history_for(self.test_search_by_tag) as history_id:
            hda_id = self.dataset_populator.new_dataset(history_id)["id"]
            update_payload = {
                "tags": ["cool:new_tag", "cool:another_tag"],
            }
            updated_hda = self._put(f"histories/{history_id}/contents/{hda_id}", update_payload, json=True).json()
            assert "cool:new_tag" in updated_hda["tags"]
            assert "cool:another_tag" in updated_hda["tags"]
            payload = {
                "limit": 10,
                "offset": 0,
                "q": ["history_content_type", "tag"],
                "qv": ["dataset", "cool:new_tag"],
                "history_id": history_id,
            }
            index_response = self._get("datasets", payload).json()
            assert len(index_response) == 1
            payload = {
                "limit": 10,
                "offset": 0,
                "q": ["history_content_type", "tag-contains"],
                "qv": ["dataset", "new_tag"],
                "history_id": history_id,
            }
            index_response = self._get("datasets", payload).json()
            assert len(index_response) == 1
            payload = {
                "limit": 10,
                "offset": 0,
                "q": ["history_content_type", "tag-contains"],
                "qv": ["dataset", "notag"],
                "history_id": history_id,
            }
            index_response = self._get("datasets", payload).json()
            assert len(index_response) == 0

    @requires_new_history
    def test_search_by_tag_case_insensitive(self):
        with self.dataset_populator.test_history_for(self.test_search_by_tag_case_insensitive) as history_id:
            hda_id = self.dataset_populator.new_dataset(history_id)["id"]
            update_payload = {
                "tags": ["name:new_TAG", "cool:another_TAG"],
            }
            updated_hda = self._put(f"histories/{history_id}/contents/{hda_id}", update_payload, json=True).json()
            assert "name:new_TAG" in updated_hda["tags"]
            assert "cool:another_TAG" in updated_hda["tags"]
            payload = {
                "limit": 10,
                "offset": 0,
                "q": ["history_content_type", "tag"],
                "qv": ["dataset", "name:new_tag"],
                "history_id": history_id,
            }
            index_response = self._get("datasets", payload).json()
            assert len(index_response) == 1
            payload = {
                "limit": 10,
                "offset": 0,
                "q": ["history_content_type", "tag-contains"],
                "qv": ["dataset", "new_tag"],
                "history_id": history_id,
            }
            index_response = self._get("datasets", payload).json()
            assert len(index_response) == 1
            payload = {
                "limit": 10,
                "offset": 0,
                "q": ["history_content_type", "tag-contains"],
                "qv": ["dataset", "notag"],
                "history_id": history_id,
            }
            index_response = self._get("datasets", payload).json()
            assert len(index_response) == 0

    @requires_new_history
    def test_search_by_tool_id(self):
        with self.dataset_populator.test_history_for(self.test_search_by_tool_id) as history_id:
            self.dataset_populator.new_dataset(history_id)
            payload = {
                "limit": 1,
                "offset": 0,
                "q": ["history_content_type", "tool_id"],
                "qv": ["dataset", "__DATA_FETCH__"],
                "history_id": history_id,
            }
            assert len(self._get("datasets", payload).json()) == 1
            payload = {
                "limit": 1,
                "offset": 0,
                "q": ["history_content_type", "tool_id"],
                "qv": ["dataset", "__DATA_FETCH__X"],
                "history_id": history_id,
            }
            assert len(self._get("datasets", payload).json()) == 0
            payload = {
                "limit": 1,
                "offset": 0,
                "q": ["history_content_type", "tool_id-contains"],
                "qv": ["dataset", "ATA_FETCH"],
                "history_id": history_id,
            }
            assert len(self._get("datasets", payload).json()) == 1
            self.dataset_collection_populator.create_list_in_history(
                history_id, name="search by tool id", contents=["1\n2\n3"], wait=True
            )
            payload = {
                "limit": 10,
                "offset": 0,
                "q": ["name", "tool_id"],
                "qv": ["search by tool id", "__DATA_FETCH__"],
                "history_id": history_id,
            }
            result = self._get("datasets", payload).json()
            assert result[0]["name"] == "search by tool id", result
            payload = {
                "limit": 1,
                "offset": 0,
                "q": ["history_content_type", "tool_id"],
                "qv": ["dataset_collection", "uploadX"],
                "history_id": history_id,
            }
            result = self._get("datasets", payload).json()
            assert len(result) == 0

    @requires_new_history
    def test_search_by_extension(self):
        with self.dataset_populator.test_history_for(self.test_search_by_extension) as history_id:
            self.dataset_populator.new_dataset(history_id, wait=True)
            payload = {
                "q": ["extension"],
                "qv": ["txt"],
                "history_id": history_id,
            }
            assert len(self._get("datasets", payload).json()) == 1
            payload = {
                "q": ["extension"],
                "qv": ["bam"],
                "history_id": history_id,
            }
            assert len(self._get("datasets", payload).json()) == 0
            payload = {
                "q": ["extension-in"],
                "qv": ["bam,txt"],
                "history_id": history_id,
            }
            assert len(self._get("datasets", payload).json()) == 1
            payload = {
                "q": ["extension-like"],
                "qv": ["t%t"],
                "history_id": history_id,
            }
            assert len(self._get("datasets", payload).json()) == 1
            payload = {
                "q": ["extension-like"],
                "qv": ["b%m"],
                "history_id": history_id,
            }
            assert len(self._get("datasets", payload).json()) == 0

    def test_invalid_search(self):
        payload = {
            "limit": 10,
            "offset": 0,
            "q": ["history_content_type", "tag-invalid_op"],
            "qv": ["dataset", "notag"],
        }
        index_response = self._get("datasets", payload)
        self._assert_status_code_is(index_response, 400)
        assert index_response.json()["err_msg"] == "bad op in filter"

    def test_search_returns_only_accessible(self, history_id):
        hda_id = self.dataset_populator.new_dataset(history_id)["id"]
        with self._different_user():
            payload = {"limit": 10, "offset": 0, "q": ["history_content_type"], "qv": ["dataset"]}
            index_response = self._get("datasets", payload).json()
            for item in index_response:
                assert hda_id != item["id"]

    def test_show(self, history_id):
        hda1 = self.dataset_populator.new_dataset(history_id)
        show_response = self._get(f"datasets/{hda1['id']}")
        self._assert_status_code_is(show_response, 200)
        self.__assert_matches_hda(hda1, show_response.json())

    def test_show_permission_denied(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id)
        self.dataset_populator.make_private(history_id=history_id, dataset_id=hda["id"])
        with self._different_user():
            show_response = self._get(f"datasets/{hda['id']}")
            self._assert_status_code_is(show_response, 403)

    @requires_admin
    def test_admin_can_update_permissions(self, history_id):
        # Create private dataset
        hda = self.dataset_populator.new_dataset(history_id)
        dataset_id = hda["id"]
        self.dataset_populator.make_private(history_id=history_id, dataset_id=dataset_id)

        # Admin removes restrictions
        payload = {"action": "remove_restrictions"}
        update_response = self._put(f"datasets/{dataset_id}/permissions", payload, admin=True, json=True)
        self._assert_status_code_is_ok(update_response)

        # Other users can access the dataset
        with self._different_user():
            show_response = self._get(f"datasets/{hda['id']}")
            self._assert_status_code_is_ok(show_response)

    def __assert_matches_hda(self, input_hda, query_hda):
        self._assert_has_keys(query_hda, "id", "name")
        assert input_hda["name"] == query_hda["name"]
        assert input_hda["id"] == query_hda["id"]

    def test_display(self, history_id):
        contents = textwrap.dedent(
            """\
        1   2   3   4
        A   B   C   D
        10  20  30  40
        """
        )
        hda1 = self.dataset_populator.new_dataset(history_id, content=contents, wait=True)
        display_response = self._get(f"histories/{history_id}/contents/{hda1['id']}/display", {"raw": "True"})
        self._assert_status_code_is(display_response, 200)
        assert display_response.text == contents

    def test_display_error_handling(self, history_id):
        hda1 = self.dataset_populator.create_deferred_hda(
            history_id, "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed"
        )
        display_response = self._get(f"histories/{history_id}/contents/{hda1['id']}/display", {"raw": "True"})
        self._assert_status_code_is(display_response, 409)
        assert (
            display_response.json()["err_msg"]
            == "The dataset you are attempting to view has deferred data. You can only use this dataset as input for jobs."
        )

    def test_get_content_as_text(self, history_id):
        contents = textwrap.dedent(
            """\
        1   2   3   4
        A   B   C   D
        10  20  30  40
        """
        )
        hda1 = self.dataset_populator.new_dataset(history_id, content=contents, wait=True)
        get_content_as_text_response = self._get(f"datasets/{hda1['id']}/get_content_as_text")
        self._assert_status_code_is(get_content_as_text_response, 200)
        self._assert_has_key(get_content_as_text_response.json(), "item_data")
        assert get_content_as_text_response.json().get("item_data") == contents

    def test_get_content_as_text_with_compressed_text_data(self, history_id):
        test_data_resolver = TestDataResolver()
        with open(test_data_resolver.get_filename("1.fasta.gz"), mode="rb") as fh:
            hda1 = self.dataset_populator.new_dataset(history_id, content=fh, ftype="fasta.gz", wait=True)
        get_content_as_text_response = self._get(f"datasets/{hda1['id']}/get_content_as_text")
        self._assert_status_code_is(get_content_as_text_response, 200)
        self._assert_has_key(get_content_as_text_response.json(), "item_data")
        assert ">hg17" in get_content_as_text_response.json().get("item_data")

    def test_anon_get_content_as_text(self, history_id):
        contents = "accessible data"
        hda1 = self.dataset_populator.new_dataset(history_id, content=contents, wait=True)
        with self._different_user(anon=True):
            get_content_as_text_response = self._get(f"datasets/{hda1['id']}/get_content_as_text")
            self._assert_status_code_is(get_content_as_text_response, 200)

    def test_anon_private_get_content_as_text(self, history_id):
        contents = "private data"
        hda1 = self.dataset_populator.new_dataset(history_id, content=contents, wait=True)
        self.dataset_populator.make_private(history_id=history_id, dataset_id=hda1["id"])
        with self._different_user(anon=True):
            get_content_as_text_response = self._get(f"datasets/{hda1['id']}/get_content_as_text")
            self._assert_status_code_is(get_content_as_text_response, 403)

    def test_dataprovider_chunk(self, history_id):
        contents = textwrap.dedent(
            """\
        1   2   3   4
        A   B   C   D
        10  20  30  40
        """
        )
        # test first chunk
        hda1 = self.dataset_populator.new_dataset(history_id, content=contents, wait=True)
        kwds = {
            "data_type": "raw_data",
            "provider": "chunk",
            "chunk_index": "0",
            "chunk_size": "5",
        }

        display_response = self._get(f"datasets/{hda1['id']}", kwds)
        self._assert_status_code_is(display_response, 200)
        display = display_response.json()
        self._assert_has_key(display, "data")
        assert display["data"] == ["1   2"]

        # test index
        kwds = {
            "data_type": "raw_data",
            "provider": "chunk",
            "chunk_index": "1",
            "chunk_size": "5",
        }

        display_response = self._get(f"datasets/{hda1['id']}", kwds)
        self._assert_status_code_is(display_response, 200)
        display = display_response.json()
        self._assert_has_key(display, "data")
        assert display["data"] == ["   3 "]

        # test line breaks
        kwds = {
            "data_type": "raw_data",
            "provider": "chunk",
            "chunk_index": "0",
            "chunk_size": "20",
        }

        display_response = self._get(f"datasets/{hda1['id']}", kwds)
        self._assert_status_code_is(display_response, 200)
        display = display_response.json()
        self._assert_has_key(display, "data")
        assert "\nA" in display["data"][0]

    def test_bam_chunking_through_display_endpoint(self, history_id):
        # This endpoint does not use data providers and instead overrides display_data
        # in the bam datatype. This is the endpoint is very close to the legacy non-API
        # controller endpoint used by the UI to produce these chunks.
        bam_dataset = self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver)
        bam_id = bam_dataset["id"]

        chunk_1 = self._display_chunk(bam_id, 0, 1)
        self._assert_has_keys(chunk_1, "offset", "ck_data")

        offset = chunk_1["offset"]

        chunk_2 = self._display_chunk(bam_id, offset, 1)
        assert chunk_2["offset"] > offset
        # chunk_1 just contains all the headers so this check wouldn't work.
        assert len(chunk_2["ck_data"].split("\n")) == 1

        double_chunk = self._display_chunk(bam_id, offset, 2)
        assert len(double_chunk["ck_data"].split("\n")) == 2

    def _display_chunk(self, dataset_id: str, offset: int, ck_size: int):
        return self.dataset_populator.display_chunk(dataset_id, offset, ck_size)

    def test_tabular_chunking_through_display_endpoint(self, history_id):
        contents = textwrap.dedent(
            """\
        1   2   3   4
        A   B   C   D
        10  20  30  40
        """
        )
        # test first chunk
        hda1 = self.dataset_populator.new_dataset(history_id, content=contents, wait=True, file_type="tabular")
        dataset_id = hda1["id"]
        chunk_1 = self._display_chunk(dataset_id, 0, 1)
        self._assert_has_keys(chunk_1, "offset", "ck_data")

        assert chunk_1["ck_data"] == "1   2   3   4"
        assert chunk_1["offset"] == 14

        chunk_2 = self._display_chunk(dataset_id, 14, 1)
        assert chunk_2["ck_data"] == "A   B   C   D"
        assert chunk_2["offset"] == 28

        chunk_3 = self._display_chunk(dataset_id, 28, 1)
        assert chunk_3["ck_data"] == "10  20  30  40"

    def test_connectivity_table_chunking_through_display_endpoint(self, history_id):
        ct_dataset = self.dataset_populator.new_dataset(
            history_id, content=open(self.test_data_resolver.get_filename("1.ct"), "rb"), file_type="ct", wait=True
        )
        dataset_id = ct_dataset["id"]
        chunk_1 = self._display_chunk(dataset_id, 0, 1)
        self._assert_has_keys(chunk_1, "offset", "ck_data")

        assert chunk_1["ck_data"] == "363	tmRNA"
        assert chunk_1["offset"] == 10, chunk_1

        chunk_2 = self._display_chunk(dataset_id, 10, 1)
        assert chunk_2["ck_data"] == "1	G	0	2	359	1"

    def test_head(self, history_id):
        hda1 = self.dataset_populator.new_dataset(history_id, wait=True)
        display_response = self._head(f"histories/{history_id}/contents/{hda1['id']}/display", {"raw": "True"})
        self._assert_status_code_is(display_response, 200)
        assert display_response.text == ""
        display_response = self._head(
            f"histories/{history_id}/contents/{hda1['id']}{hda1['id']}/display", {"raw": "True"}
        )
        self._assert_status_code_is(display_response, 400)

    def test_byte_range_support(self, history_id):
        hda1 = self.dataset_populator.new_dataset(history_id, wait=True)
        head_response = self._head(f"histories/{history_id}/contents/{hda1['id']}/display", {"raw": "True"})
        self._assert_status_code_is(head_response, 200)
        assert head_response.headers["content-length"] == "12"
        assert head_response.text == ""
        assert head_response.headers["accept-ranges"] == "bytes"
        valid_headers = {"range": "bytes=0-0"}
        display_response = self._get(
            f"histories/{history_id}/contents/{hda1['id']}/display", {"raw": "True"}, headers=valid_headers
        )
        self._assert_status_code_is(display_response, 206)
        assert len(display_response.text) == 1
        assert display_response.headers["content-length"] == "1"
        assert display_response.headers["content-range"] == "bytes 0-0/12"
        invalid_headers = {"range": "bytes=-1-1"}
        display_response = self._get(
            f"histories/{history_id}/contents/{hda1['id']}/display", {"raw": "True"}, headers=invalid_headers
        )
        self._assert_status_code_is(display_response, 416)

    def test_tag_change(self, history_id):
        hda_id = self.dataset_populator.new_dataset(history_id)["id"]
        payload = {
            "item_id": hda_id,
            "item_class": "HistoryDatasetAssociation",
            "item_tags": ["cool:tag_a", "cool:tag_b", "tag_c", "name:tag_d", "#tag_e"],
        }

        put_response = self._put("tags", data=payload, json=True)
        self._assert_status_code_is_ok(put_response)
        updated_hda = self._get(f"histories/{history_id}/contents/{hda_id}").json()
        assert "cool:tag_a" in updated_hda["tags"]
        assert "cool:tag_b" in updated_hda["tags"]
        assert "tag_c" in updated_hda["tags"]
        assert "name:tag_d" in updated_hda["tags"]
        assert "name:tag_e" in updated_hda["tags"]

    def test_anon_tag_permissions(self):
        with self._different_user(anon=True):
            history_id = self._get(urllib.parse.urljoin(self.url, "history/current_history_json")).json()["id"]
            hda_id = self.dataset_populator.new_dataset(history_id, content="abc", wait=True)["id"]
            payload = {
                "item_id": hda_id,
                "item_class": "HistoryDatasetAssociation",
                "item_tags": ["cool:tag_a", "cool:tag_b", "tag_c", "name:tag_d", "#tag_e"],
            }
            put_response = self._put("tags", data=payload, json=True)
            updated_hda = self._get(f"histories/{history_id}/contents/{hda_id}").json()
            assert len(updated_hda["tags"]) == 5
            # ensure we can remove these tags again
            payload = {
                "item_id": hda_id,
                "item_class": "HistoryDatasetAssociation",
                "item_tags": [],
            }
            put_response = self._put("tags", data=payload, json=True)
            put_response.raise_for_status()
            updated_hda = self._get(f"histories/{history_id}/contents/{hda_id}").json()
            assert len(updated_hda["tags"]) == 0
        with self._different_user(anon=True):
            # another anon user can't modify tags
            payload = {
                "item_id": hda_id,
                "item_class": "HistoryDatasetAssociation",
                "item_tags": ["cool:tag_a", "cool:tag_b", "tag_c", "name:tag_d", "#tag_e"],
            }
            put_response = self._put("tags", data=payload, json=True)
            updated_hda = self._get(f"histories/{history_id}/contents/{hda_id}").json()
            assert len(updated_hda["tags"]) == 0

    @skip_without_tool("cat_data_and_sleep")
    def test_update_datatype(self, history_id):
        hda_id = self.dataset_populator.new_dataset(history_id)["id"]
        original_hda = self._get(f"histories/{history_id}/contents/{hda_id}").json()
        assert original_hda["extension"] == "txt"
        assert original_hda["data_type"] == "galaxy.datatypes.data.Text"

        inputs = {
            "input1": {"src": "hda", "id": hda_id},
            "sleep_time": 10,
        }
        run_response = self.dataset_populator.run_tool_raw(
            "cat_data_and_sleep",
            inputs,
            history_id,
        )
        queued_id = run_response.json()["outputs"][0]["id"]

        update_while_incomplete_response = self._put(  # try updating datatype while used as output of a running job
            f"histories/{history_id}/contents/{queued_id}", data={"datatype": "tabular"}, json=True
        )
        self._assert_status_code_is(update_while_incomplete_response, 400)

        self.dataset_populator.wait_for_history_jobs(history_id)  # now wait for upload to complete

        successful_updated_hda_response = self._put(
            f"histories/{history_id}/contents/{hda_id}", data={"datatype": "tabular"}, json=True
        ).json()
        assert successful_updated_hda_response["extension"] == "tabular"
        assert successful_updated_hda_response["data_type"] == "galaxy.datatypes.tabular.Tabular"

        invalidly_updated_hda_response = self._put(  # try updating with invalid datatype
            f"histories/{history_id}/contents/{hda_id}", data={"datatype": "invalid"}, json=True
        )
        self._assert_status_code_is(invalidly_updated_hda_response, 400)

    @skip_without_tool("cat_data_and_sleep")
    def test_delete_cancels_job(self, history_id):
        self._run_cancel_job(history_id, use_query_params=False)

    @skip_without_tool("cat_data_and_sleep")
    def test_delete_cancels_job_with_query_params(self, history_id):
        self._run_cancel_job(history_id, use_query_params=True)

    def _run_cancel_job(self, history_id: str, use_query_params: bool = False):
        hda_id = self.dataset_populator.new_dataset(history_id)["id"]
        inputs = {
            "input1": {"src": "hda", "id": hda_id},
            "sleep_time": 10,
        }
        run_response = self.dataset_populator.run_tool_raw(
            "cat_data_and_sleep",
            inputs,
            history_id,
        ).json()
        output_hda_id = run_response["outputs"][0]["id"]
        job_id = run_response["jobs"][0]["id"]

        job_details = self.dataset_populator.get_job_details(job_id).json()
        assert job_details["state"] in ("new", "queued", "running"), job_details

        # Use stop_job to cancel the creating job
        delete_response = self.dataset_populator.delete_dataset(
            history_id, output_hda_id, stop_job=True, use_query_params=use_query_params
        )
        self._assert_status_code_is_ok(delete_response)
        deleted_hda = delete_response.json()
        assert deleted_hda["deleted"], deleted_hda

        # The job should be cancelled
        deleted_job_details = self.dataset_populator.get_job_details(job_id).json()
        assert deleted_job_details["state"] in ("deleting", "deleted"), deleted_job_details

    def test_purge_does_not_reset_file_size(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="ABC", wait=True)
            assert dataset["file_size"]
            self.dataset_populator.delete_dataset(
                history_id=history_id, content_id=dataset["id"], purge=True, wait_for_purge=True
            )
            purged_dataset = self.dataset_populator.get_history_dataset_details(
                history_id=history_id, content_id=dataset["id"]
            )
            assert purged_dataset["purged"]
            assert dataset["file_size"] == purged_dataset["file_size"]

    def test_delete_batch(self):
        num_datasets = 4
        dataset_map: Dict[int, str] = {}
        history_id = self.dataset_populator.new_history()
        for index in range(num_datasets):
            hda = self.dataset_populator.new_dataset(history_id)
            dataset_map[index] = hda["id"]

        self.dataset_populator.wait_for_history(history_id)

        expected_deleted_source_ids = [
            {"id": dataset_map[1], "src": "hda"},
            {"id": dataset_map[2], "src": "hda"},
        ]
        delete_payload = {"datasets": expected_deleted_source_ids}
        deleted_result = self._delete_batch_with_payload(delete_payload)

        assert deleted_result["success_count"] == len(expected_deleted_source_ids)
        for deleted_source_id in expected_deleted_source_ids:
            dataset = self._get(f"histories/{history_id}/contents/{deleted_source_id['id']}").json()
            assert dataset["deleted"] is True

        expected_purged_source_ids = [
            {"id": dataset_map[0], "src": "hda"},
            {"id": dataset_map[2], "src": "hda"},
        ]
        purge_payload = {"purge": True, "datasets": expected_purged_source_ids}
        deleted_result = self._delete_batch_with_payload(purge_payload)

        assert deleted_result["success_count"] == len(expected_purged_source_ids)

        for purged_source_id in expected_purged_source_ids:
            self.dataset_populator.wait_for_purge(history_id, purged_source_id["id"])

    def test_delete_batch_error(self):
        num_datasets = 4
        dataset_map: Dict[int, str] = {}

        with self._different_user():
            history_id = self.dataset_populator.new_history()
            for index in range(num_datasets):
                hda = self.dataset_populator.new_dataset(history_id)
                dataset_map[index] = hda["id"]

            # Trying to delete datasets of wrong type will error
            expected_errored_source_ids = [
                {"id": dataset_map[0], "src": "ldda"},
                {"id": dataset_map[3], "src": "ldda"},
            ]
            delete_payload = {"datasets": expected_errored_source_ids}
            deleted_result = self._delete_batch_with_payload(delete_payload)

            assert deleted_result["success_count"] == 0
            assert len(deleted_result["errors"]) == len(expected_errored_source_ids)

        # Trying to delete datasets that we don't own will error
        expected_errored_source_ids = [
            {"id": dataset_map[1], "src": "hda"},
            {"id": dataset_map[2], "src": "hda"},
        ]
        delete_payload = {"datasets": expected_errored_source_ids}
        deleted_result = self._delete_batch_with_payload(delete_payload)

        assert deleted_result["success_count"] == 0
        assert len(deleted_result["errors"]) == len(expected_errored_source_ids)
        for error in deleted_result["errors"]:
            self._assert_has_keys(error, "dataset", "error_message")
            self._assert_has_keys(error["dataset"], "id", "src")

    def _delete_batch_with_payload(self, payload):
        delete_response = self._delete("datasets", data=payload, json=True)
        self._assert_status_code_is_ok(delete_response)
        deleted_result = delete_response.json()
        return deleted_result

    @skip_without_datatype("velvet")
    def test_composite_datatype_download(self, history_id):
        output = self.dataset_populator.fetch_hda(history_id, COMPOSITE_DATA_FETCH_REQUEST_1, wait=True)
        response = self._get(f"histories/{history_id}/contents/{output['id']}/display?to_ext=zip")
        self._assert_status_code_is(response, 200)
        archive = zipfile.ZipFile(BytesIO(response.content))
        namelist = archive.namelist()
        assert len(namelist) == 4, f"Expected 3 elements in [{namelist}]"

    def test_compute_md5_on_primary_dataset(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id, wait=True)
        hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda)
        assert "hashes" in hda_details, str(hda_details.keys())
        hashes = hda_details["hashes"]
        assert len(hashes) == 0

        self.dataset_populator.compute_hash(hda["id"])
        hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda)
        self.assert_hash_value(hda_details, "940cbe15c94d7e339dc15550f6bdcf4d", "MD5")

    def test_compute_sha1_on_composite_dataset(self, history_id):
        output = self.dataset_populator.fetch_hda(history_id, COMPOSITE_DATA_FETCH_REQUEST_1, wait=True)
        hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output)
        assert "hashes" in hda_details, str(hda_details.keys())
        hashes = hda_details["hashes"]
        assert len(hashes) == 0

        self.dataset_populator.compute_hash(hda_details["id"], hash_function="SHA-256", extra_files_path="Roadmaps")
        hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output)
        self.assert_hash_value(
            hda_details,
            "3cbd311889963528954fe03b28b68a09685ea7a75660bd2268d5b44cafbe0d22",
            "SHA-256",
            extra_files_path="Roadmaps",
        )

    def test_duplicated_hash_requests_on_primary(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id, wait=True)
        hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda)
        assert "hashes" in hda_details, str(hda_details.keys())
        hashes = hda_details["hashes"]
        assert len(hashes) == 0

        self.dataset_populator.compute_hash(hda["id"])
        self.dataset_populator.compute_hash(hda["id"])
        hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda)
        self.assert_hash_value(hda_details, "940cbe15c94d7e339dc15550f6bdcf4d", "MD5")

    def test_duplicated_hash_requests_on_extra_files(self, history_id):
        output = self.dataset_populator.fetch_hda(history_id, COMPOSITE_DATA_FETCH_REQUEST_1, wait=True)
        hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output)
        assert "hashes" in hda_details, str(hda_details.keys())
        hashes = hda_details["hashes"]
        assert len(hashes) == 0

        # 4 unique requests, but make them twice...
        for _ in range(2):
            self.dataset_populator.compute_hash(hda_details["id"], hash_function="SHA-256", extra_files_path="Roadmaps")
            self.dataset_populator.compute_hash(hda_details["id"], hash_function="SHA-1", extra_files_path="Roadmaps")
            self.dataset_populator.compute_hash(hda_details["id"], hash_function="MD5", extra_files_path="Roadmaps")
            self.dataset_populator.compute_hash(
                hda_details["id"], hash_function="SHA-256", extra_files_path="Sequences"
            )

        hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output)
        self.assert_hash_value(hda_details, "ce0c0ef1073317ff96c896c249b002dc", "MD5", extra_files_path="Roadmaps")
        self.assert_hash_value(
            hda_details, "fe2e06cdd03922a1ddf3fe6c7e0d299c8044fc8e", "SHA-1", extra_files_path="Roadmaps"
        )
        self.assert_hash_value(
            hda_details,
            "3cbd311889963528954fe03b28b68a09685ea7a75660bd2268d5b44cafbe0d22",
            "SHA-256",
            extra_files_path="Roadmaps",
        )
        self.assert_hash_value(
            hda_details,
            "4688dca47fe3214516c35acd284a79d97bd6df2bc1c55981b556d995495b91b6",
            "SHA-256",
            extra_files_path="Sequences",
        )

    def assert_hash_value(self, dataset_details, expected_hash_value, hash_function, extra_files_path=None):
        assert "hashes" in dataset_details, str(dataset_details.keys())
        hashes = dataset_details["hashes"]
        matching_hashes = [
            h for h in hashes if h["extra_files_path"] == extra_files_path and h["hash_function"] == hash_function
        ]
        assert len(matching_hashes) == 1
        hash_value = matching_hashes[0]["hash_value"]
        assert expected_hash_value == hash_value

    def test_storage_show(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id, wait=True)
        hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda)
        dataset_id = hda_details["dataset_id"]
        storage_info_dict = self.dataset_populator.dataset_storage_info(dataset_id)
        assert_has_keys(storage_info_dict, "object_store_id", "name", "description")

    def test_storage_show_on_discarded(self, history_id):
        as_list = self.dataset_populator.create_contents_from_store(
            history_id,
            store_dict=one_hda_model_store_dict(),
        )
        assert len(as_list) == 1
        hda_id = as_list[0]["id"]
        storage_info_dict = self.dataset_populator.dataset_storage_info(hda_id)
        assert_has_keys(storage_info_dict, "object_store_id", "name", "description", "sources", "hashes")

        assert storage_info_dict["object_store_id"] is None
        sources = storage_info_dict["sources"]
        assert len(sources) == 1
        assert sources[0]["source_uri"] == TEST_SOURCE_URI

    def test_storage_show_on_deferred(self, history_id):
        as_list = self.dataset_populator.create_contents_from_store(
            history_id,
            store_dict=deferred_hda_model_store_dict(),
        )
        assert len(as_list) == 1
        hda_id = as_list[0]["id"]
        storage_info_dict = self.dataset_populator.dataset_storage_info(hda_id)
        assert_has_keys(storage_info_dict, "object_store_id", "name", "description", "sources", "hashes")

        assert storage_info_dict["object_store_id"] is None
        sources = storage_info_dict["sources"]
        assert len(sources) == 1
        assert sources[0]["source_uri"] == TEST_SOURCE_URI

    @skip_if_github_down
    def test_display_application_link(self, history_id):
        item = {
            "src": "url",
            "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bam",
            "ext": "bam",
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        dataset_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output, assert_ok=True)
        assert "display_application/" in dataset_details["display_apps"][0]["links"][0]["href"]

    def test_cannot_update_datatype_on_immutable_history(self, history_id):
        hda_id = self.dataset_populator.new_dataset(history_id)["id"]
        self.dataset_populator.wait_for_history_jobs(history_id)

        # once we purge the history, it becomes immutable
        self._delete(f"histories/{history_id}", data={"purge": True}, json=True)

        # now we can't update the datatype
        response = self._put(f"histories/{history_id}/contents/{hda_id}", data={"datatype": "tabular"}, json=True)
        self._assert_status_code_is(response, 403)
        assert response.json()["err_msg"] == "History is immutable"

    def test_download_non_english_characters(self, history_id):
        name = "دیتاست"
        hda = self.dataset_populator.new_dataset(history_id=history_id, name=name, content="data", wait=True)
        response = self._get(f"histories/{history_id}/contents/{hda['id']}/display?to_ext=json")
        self._assert_status_code_is(response, 200)
        assert quote(name, safe="") in response.headers["Content-Disposition"]

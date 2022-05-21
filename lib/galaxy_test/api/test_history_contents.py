import time
import urllib.parse
from datetime import datetime
from typing import (
    Any,
    List,
    Optional,
    Tuple,
)

from galaxy.webapps.galaxy.services.history_contents import DirectionOptions
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    LibraryPopulator,
    skip_without_tool,
)
from ._framework import ApiTestCase


# TODO: Test anonymous access.
class HistoryContentsApiTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    def test_index_hda_summary(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id)
        contents_response = self._get(f"histories/{self.history_id}/contents")
        hda_summary = self.__check_for_hda(contents_response, hda1)
        assert "display_types" not in hda_summary  # Quick summary, not full details

    def test_make_private_and_public(self):
        hda1 = self._wait_for_new_hda()
        update_url = f"histories/{self.history_id}/contents/{hda1['id']}/permissions"

        role_id = self.dataset_populator.user_private_role_id()
        # Give manage permission to the user.
        payload = {
            "access": [],
            "manage": [role_id],
        }
        update_response = self._update_permissions(update_url, payload, admin=True)
        self._assert_status_code_is(update_response, 200)
        self._assert_other_user_can_access(hda1["id"])
        # Then we restrict access.
        payload = {
            "action": "make_private",
        }
        update_response = self._update_permissions(update_url, payload)
        self._assert_status_code_is(update_response, 200)
        self._assert_other_user_cannot_access(hda1["id"])

        # Then we restrict access.
        payload = {
            "action": "remove_restrictions",
        }
        update_response = self._update_permissions(update_url, payload)
        self._assert_status_code_is(update_response, 200)
        self._assert_other_user_can_access(hda1["id"])

    def test_set_permissions_add_admin_history_contents(self):
        self._verify_dataset_permissions("history_contents")

    def test_set_permissions_add_admin_datasets(self):
        self._verify_dataset_permissions("dataset")

    def _verify_dataset_permissions(self, api_endpoint):
        hda1 = self._wait_for_new_hda()
        hda_id = hda1["id"]
        if api_endpoint == "history_contents":
            update_url = f"histories/{self.history_id}/contents/{hda_id}/permissions"
        else:
            update_url = f"datasets/{hda_id}/permissions"

        role_id = self.dataset_populator.user_private_role_id()

        payload = {
            "access": [role_id],
            "manage": [role_id],
        }

        # Other users cannot modify permissions.
        with self._different_user():
            update_response = self._update_permissions(update_url, payload)
            self._assert_status_code_is(update_response, 403)

        # First the details render for another user.
        self._assert_other_user_can_access(hda_id)

        # Then we restrict access.
        update_response = self._update_permissions(update_url, payload, admin=True)
        self._assert_status_code_is(update_response, 200)

        # Finally the details don't render.
        self._assert_other_user_cannot_access(hda_id)

        # But they do for the original user.
        contents_response = self._get(f"histories/{self.history_id}/contents/{hda_id}").json()
        assert "name" in contents_response

        update_response = self._update_permissions(update_url, payload)
        self._assert_status_code_is(update_response, 200)

        payload = {
            "access": [role_id],
            "manage": [role_id],
        }
        update_response = self._update_permissions(update_url, payload)
        self._assert_status_code_is(update_response, 200)
        self._assert_other_user_cannot_access(hda_id)

        user_id = self.dataset_populator.user_id()
        with self._different_user():
            different_user_id = self.dataset_populator.user_id()
        combined_user_role = self.dataset_populator.create_role(
            [user_id, different_user_id], description="role for testing permissions"
        )

        payload = {
            "access": [combined_user_role["id"]],
            "manage": [role_id],
        }
        update_response = self._update_permissions(update_url, payload)
        self._assert_status_code_is(update_response, 200)
        # Now other user can see dataset again with access permission.
        self._assert_other_user_can_access(hda_id)
        # access doesn't imply management though...
        with self._different_user():
            update_response = self._update_permissions(update_url, payload)
            self._assert_status_code_is(update_response, 403)

    def _assert_other_user_cannot_access(self, history_content_id):
        with self._different_user():
            contents_response = self.dataset_populator.get_history_dataset_details_raw(
                history_id=self.history_id, dataset_id=history_content_id
            )
            assert contents_response.status_code == 403

    def _assert_other_user_can_access(self, history_content_id):
        with self._different_user():
            contents_response = self.dataset_populator.get_history_dataset_details_raw(
                history_id=self.history_id, dataset_id=history_content_id
            )
            contents_response.raise_for_status()
            assert "name" in contents_response.json()

    def test_index_hda_all_details(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id)
        contents_response = self._get(f"histories/{self.history_id}/contents?details=all")
        hda_details = self.__check_for_hda(contents_response, hda1)
        self.__assert_hda_has_full_details(hda_details)

    def test_index_hda_detail_by_id(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id)
        contents_response = self._get(f"histories/{self.history_id}/contents?details={hda1['id']}")
        hda_details = self.__check_for_hda(contents_response, hda1)
        self.__assert_hda_has_full_details(hda_details)

    def test_show_hda(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id)
        show_response = self.__show(hda1)
        self._assert_status_code_is(show_response, 200)
        self.__assert_matches_hda(hda1, show_response.json())

    def _create_copy(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id)
        create_data = dict(
            source="hda",
            content=hda1["id"],
        )
        second_history_id = self.dataset_populator.new_history()
        assert self.__count_contents(second_history_id) == 0
        create_response = self._post(f"histories/{second_history_id}/contents", create_data, json=True)
        self._assert_status_code_is(create_response, 200)
        return create_response.json()

    def test_hda_copy(self):
        response = self._create_copy()
        assert self.__count_contents(response["history_id"]) == 1

    def test_inheritance_chain(self):
        response = self._create_copy()
        inheritance_chain_response = self._get(f"datasets/{response['id']}/inheritance_chain")
        self._assert_status_code_is_ok(inheritance_chain_response)
        inheritance_chain = inheritance_chain_response.json()
        assert len(inheritance_chain) == 1

    def test_library_copy(self):
        ld = self.library_populator.new_library_dataset("lda_test_library")
        create_data = dict(
            source="library",
            content=ld["id"],
        )
        assert self.__count_contents(self.history_id) == 0
        create_response = self._post(f"histories/{self.history_id}/contents", create_data, json=True)
        self._assert_status_code_is(create_response, 200)
        assert self.__count_contents(self.history_id) == 1

    def test_update(self):
        hda1 = self._wait_for_new_hda()
        assert str(hda1["deleted"]).lower() == "false"
        update_response = self._update(hda1["id"], dict(deleted=True))
        self._assert_status_code_is(update_response, 200)
        show_response = self.__show(hda1)
        assert str(show_response.json()["deleted"]).lower() == "true"

        update_response = self._update(hda1["id"], dict(name="Updated Name"))
        assert self.__show(hda1).json()["name"] == "Updated Name"

        update_response = self._update(hda1["id"], dict(name="Updated Name"))
        assert self.__show(hda1).json()["name"] == "Updated Name"

        unicode_name = "ржевский сапоги"
        update_response = self._update(hda1["id"], dict(name=unicode_name))
        updated_hda = self.__show(hda1).json()
        assert updated_hda["name"] == unicode_name, updated_hda

        quoted_name = '"Mooo"'
        update_response = self._update(hda1["id"], dict(name=quoted_name))
        updated_hda = self.__show(hda1).json()
        assert updated_hda["name"] == quoted_name, quoted_name

        data = {
            "dataset_id": hda1["id"],
            "name": "moocow",
            "dbkey": "?",
            "annotation": None,
            "info": "my info is",
            "operation": "attributes",
        }
        update_response = self._set_edit_update(data)
        # No key or anything supplied, expect a permission problem.
        # A bit questionable but I think this is a 400 instead of a 403 so that
        # we don't distinguish between this is a valid ID you don't have access to
        # and this is an invalid ID.
        assert update_response.status_code == 400, update_response.content

    def test_update_batch(self):
        hda1 = self._wait_for_new_hda()
        assert str(hda1["deleted"]).lower() == "false"
        assert str(hda1["visible"]).lower() == "true"

        # update deleted flag => true
        payload = dict(items=[{"history_content_type": "dataset", "id": hda1["id"]}], deleted=True)
        update_response = self._update_batch(payload)
        objects = update_response.json()
        assert objects[0]["deleted"] is True
        assert objects[0]["visible"] is True

        # update visibility flag => false
        payload = dict(items=[{"history_content_type": "dataset", "id": hda1["id"]}], visible=False)
        update_response = self._update_batch(payload)
        objects = update_response.json()
        assert objects[0]["deleted"] is True
        assert objects[0]["visible"] is False

        # update both flags
        payload = dict(items=[{"history_content_type": "dataset", "id": hda1["id"]}], deleted=False, visible=True)
        update_response = self._update_batch(payload)
        objects = update_response.json()
        assert objects[0]["deleted"] is False
        assert objects[0]["visible"] is True

    def test_update_batch_collections(self):
        hdca = self._create_pair_collection()
        assert hdca["deleted"] is False
        assert hdca["visible"] is True

        # update deleted flag => true
        payload = dict(items=[{"history_content_type": "dataset_collection", "id": hdca["id"]}], deleted=True)
        update_response = self._update_batch(payload)
        objects = update_response.json()
        assert objects[0]["deleted"] is True
        assert objects[0]["visible"] is True

        # update visibility flag => false
        payload = dict(items=[{"history_content_type": "dataset_collection", "id": hdca["id"]}], visible=False)
        update_response = self._update_batch(payload)
        objects = update_response.json()
        assert objects[0]["deleted"] is True
        assert objects[0]["visible"] is False

        # update both flags
        payload = dict(
            items=[{"history_content_type": "dataset_collection", "id": hdca["id"]}], deleted=False, visible=True
        )
        update_response = self._update_batch(payload)
        objects = update_response.json()
        assert objects[0]["deleted"] is False
        assert objects[0]["visible"] is True

    def test_update_type_failures(self):
        hda1 = self._wait_for_new_hda()
        update_response = self._update(hda1["id"], dict(deleted="not valid"))
        self._assert_status_code_is(update_response, 400)

    def _wait_for_new_hda(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id)
        self.dataset_populator.wait_for_history(self.history_id)
        return hda1

    def _set_edit_update(self, data):
        update_response = self._put(urllib.parse.urljoin(self.url, "dataset/set_edit"), data=data, json=True)
        return update_response

    def _update(self, item_id, data, admin=False, history_id=None):
        history_id = history_id or self.history_id
        update_response = self._put(f"histories/{history_id}/contents/{item_id}", data=data, json=True, admin=admin)
        return update_response

    def _update_permissions(self, url, data, admin=False):
        update_response = self._put(url, data=data, json=True, admin=admin)
        return update_response

    def _update_batch(self, data):
        update_response = self._put(f"histories/{self.history_id}/contents", data=data, json=True)
        return update_response

    def test_delete(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id)
        self.dataset_populator.wait_for_history(self.history_id)
        assert str(self.__show(hda1).json()["deleted"]).lower() == "false"
        delete_response = self._delete(f"histories/{self.history_id}/contents/{hda1['id']}")
        assert delete_response.status_code < 300  # Something in the 200s :).
        assert str(self.__show(hda1).json()["deleted"]).lower() == "true"

    def test_delete_anon(self):
        with self._different_user(anon=True):
            history_id = self._get(urllib.parse.urljoin(self.url, "history/current_history_json")).json()["id"]
            hda1 = self.dataset_populator.new_dataset(history_id)
            self.dataset_populator.wait_for_history(history_id)
            assert str(self.__show(hda1).json()["deleted"]).lower() == "false"
            delete_response = self._delete(f"histories/{history_id}/contents/{hda1['id']}")
            assert delete_response.status_code < 300  # Something in the 200s :).
            assert str(self.__show(hda1).json()["deleted"]).lower() == "true"

    def test_delete_permission_denied(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id)
        with self._different_user(anon=True):
            delete_response = self._delete(f"histories/{self.history_id}/contents/{hda1['id']}")
            assert delete_response.status_code == 403
            assert delete_response.json()["err_msg"] == "HistoryDatasetAssociation is not owned by user"

    def test_purge(self):
        hda1 = self.dataset_populator.new_dataset(self.history_id)
        self.dataset_populator.wait_for_history(self.history_id)
        assert str(self.__show(hda1).json()["deleted"]).lower() == "false"
        assert str(self.__show(hda1).json()["purged"]).lower() == "false"
        data = {"purge": True}
        delete_response = self._delete(f"histories/{self.history_id}/contents/{hda1['id']}", data=data, json=True)
        assert delete_response.status_code < 300  # Something in the 200s :).
        # Purging and deleting the dataset may or may not happen asynchronously.
        # On 202 the request was accepted and purging will happen later.
        if delete_response.status_code == 202:
            self.dataset_populator.wait_for_purge(self.history_id, hda1["id"])
        else:
            assert self.__show(hda1).json()["deleted"]
            assert self.__show(hda1).json()["purged"]

    def test_dataset_collection_creation_on_contents(self):
        payload = self.dataset_collection_populator.create_pair_payload(
            self.history_id, type="dataset_collection", wait=True
        )
        endpoint = "tools/fetch"
        self._check_pair_creation(endpoint, payload)

    def test_dataset_collection_creation_on_typed_contents(self):
        payload = self.dataset_collection_populator.create_pair_payload(self.history_id, wait=True)
        endpoint = "tools/fetch"
        self._check_pair_creation(endpoint, payload)

    def test_dataset_collection_create_from_exisiting_datasets_with_new_tags(self):
        with self.dataset_populator.test_history() as history_id:
            hda_id = self.dataset_populator.new_dataset(history_id, content="1 2 3")["id"]
            hda2_id = self.dataset_populator.new_dataset(history_id, content="1 2 3")["id"]
            update_response = self._update(hda2_id, dict(tags=["existing:tag"]), history_id=history_id).json()
            assert update_response["tags"] == ["existing:tag"]
            creation_payload = {
                "collection_type": "list",
                "history_id": history_id,
                "element_identifiers": [
                    {"id": hda_id, "src": "hda", "name": "element_id1", "tags": ["my_new_tag"]},
                    {"id": hda2_id, "src": "hda", "name": "element_id2", "tags": ["another_new_tag"]},
                ],
                "type": "dataset_collection",
                "copy_elements": True,
            }
            r = self._post(f"histories/{self.history_id}/contents", creation_payload, json=True).json()
            assert r["elements"][0]["object"]["id"] != hda_id, "HDA has not been copied"
            assert len(r["elements"][0]["object"]["tags"]) == 1
            assert r["elements"][0]["object"]["tags"][0] == "my_new_tag"
            assert len(r["elements"][1]["object"]["tags"]) == 2, r["elements"][1]["object"]["tags"]
            original_hda = self.dataset_populator.get_history_dataset_details(history_id=history_id, dataset_id=hda_id)
            assert len(original_hda["tags"]) == 0, original_hda["tags"]

    def _check_pair_creation(self, endpoint, payload):
        pre_collection_count = self.__count_contents(type="dataset_collection")
        pre_dataset_count = self.__count_contents(type="dataset")
        pre_combined_count = self.__count_contents(type="dataset,dataset_collection")

        dataset_collection_response = self._post(endpoint, payload, json=True)

        dataset_collection = self.__check_create_collection_response(dataset_collection_response)

        post_collection_count = self.__count_contents(type="dataset_collection")
        post_dataset_count = self.__count_contents(type="dataset")
        post_combined_count = self.__count_contents(type="dataset,dataset_collection")

        # Test filtering types with index.
        assert pre_collection_count == 0
        assert post_collection_count == 1
        assert post_combined_count == pre_dataset_count + 1
        assert post_combined_count == pre_combined_count + 1
        assert pre_dataset_count == post_dataset_count

        # Test show dataset colleciton.
        collection_url = f"histories/{self.history_id}/contents/dataset_collections/{dataset_collection['id']}"
        show_response = self._get(collection_url)
        self._assert_status_code_is(show_response, 200)
        dataset_collection = show_response.json()
        self._assert_has_keys(dataset_collection, "url", "name", "deleted")

        assert not dataset_collection["deleted"]

        delete_response = self._delete(collection_url)
        self._assert_status_code_is(delete_response, 200)

        show_response = self._get(collection_url)
        dataset_collection = show_response.json()
        assert dataset_collection["deleted"]

    @skip_without_tool("collection_creates_list")
    def test_jobs_summary_simple_hdca(self):
        fetch_response = self.dataset_collection_populator.create_list_in_history(
            self.history_id, contents=["a\nb\nc\nd", "e\nf\ng\nh"]
        ).json()
        hdca_id = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)["id"]
        run = self.dataset_populator.run_collection_creates_list(self.history_id, hdca_id)
        collections = run["output_collections"]
        collection = collections[0]
        jobs_summary_url = f"histories/{self.history_id}/contents/dataset_collections/{collection['id']}/jobs_summary"
        jobs_summary_response = self._get(jobs_summary_url)
        self._assert_status_code_is(jobs_summary_response, 200)
        jobs_summary = jobs_summary_response.json()
        self._assert_has_keys(jobs_summary, "populated_state", "states")

    @skip_without_tool("cat1")
    def test_jobs_summary_implicit_hdca(self):
        create_response = self.dataset_collection_populator.create_pair_in_history(
            self.history_id, contents=["123", "456"], wait=True
        )
        hdca_id = create_response.json()["outputs"][0]["id"]
        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        run = self.dataset_populator.run_tool("cat1", inputs=inputs, history_id=self.history_id)
        self.dataset_populator.wait_for_history_jobs(self.history_id)
        collections = run["implicit_collections"]
        collection = collections[0]
        jobs_summary_url = f"histories/{self.history_id}/contents/dataset_collections/{collection['id']}/jobs_summary"
        jobs_summary_response = self._get(jobs_summary_url)
        self._assert_status_code_is(jobs_summary_response, 200)
        jobs_summary = jobs_summary_response.json()
        self._assert_has_keys(jobs_summary, "populated_state", "states")
        states = jobs_summary["states"]
        assert states.get("ok") == 2, states

    def test_dataset_collection_hide_originals(self):
        payload = self.dataset_collection_populator.create_pair_payload(
            self.history_id, type="dataset_collection", direct_upload=False
        )

        payload["hide_source_items"] = True
        dataset_collection_response = self._post(f"histories/{self.history_id}/contents", payload, json=True)
        self.__check_create_collection_response(dataset_collection_response)

        contents_response = self._get(f"histories/{self.history_id}/contents")
        datasets = [
            d for d in contents_response.json() if d["history_content_type"] == "dataset" and d["hid"] in [1, 2]
        ]
        # Assert two datasets in source were hidden.
        assert len(datasets) == 2
        assert not datasets[0]["visible"]
        assert not datasets[1]["visible"]

    def test_update_dataset_collection(self):
        hdca = self._create_pair_collection()
        body = dict(name="newnameforpair")
        update_response = self._put(
            f"histories/{self.history_id}/contents/dataset_collections/{hdca['id']}", data=body, json=True
        )
        self._assert_status_code_is(update_response, 200)
        show_response = self.__show(hdca)
        assert str(show_response.json()["name"]) == "newnameforpair"

    def test_update_batch_dataset_collection(self):
        hdca = self._create_pair_collection()
        body = {"items": [{"history_content_type": "dataset_collection", "id": hdca["id"]}], "name": "newnameforpair"}
        update_response = self._put(f"histories/{self.history_id}/contents", data=body, json=True)
        self._assert_status_code_is(update_response, 200)
        show_response = self.__show(hdca)
        assert str(show_response.json()["name"]) == "newnameforpair"

    def _create_pair_collection(self):
        payload = self.dataset_collection_populator.create_pair_payload(self.history_id, type="dataset_collection")
        dataset_collection_response = self._post("tools/fetch", payload, json=True)
        self._assert_status_code_is(dataset_collection_response, 200)
        hdca = dataset_collection_response.json()["output_collections"][0]
        return hdca

    def test_hdca_copy(self):
        hdca = self.dataset_collection_populator.create_pair_in_history(self.history_id, wait=True).json()
        hdca_id = hdca["outputs"][0]["id"]
        second_history_id = self.dataset_populator.new_history()
        create_data = dict(
            source="hdca",
            content=hdca_id,
        )
        assert len(self._get(f"histories/{second_history_id}/contents/dataset_collections").json()) == 0
        create_response = self._post(
            f"histories/{second_history_id}/contents/dataset_collections", create_data, json=True
        )
        self.__check_create_collection_response(create_response)
        contents = self._get(f"histories/{second_history_id}/contents/dataset_collections").json()
        assert len(contents) == 1
        new_forward, _ = self.__get_paired_response_elements(contents[0])
        self._assert_has_keys(new_forward, "history_id")
        assert new_forward["history_id"] == self.history_id

    def test_hdca_copy_with_new_dbkey(self):
        fetch_response = self.dataset_collection_populator.create_pair_in_history(self.history_id, wait=True).json()
        hdca = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        hdca_id = hdca["id"]
        assert hdca["elements"][0]["object"]["metadata_dbkey"] == "?"
        assert hdca["elements"][0]["object"]["genome_build"] == "?"
        create_data = {"source": "hdca", "content": hdca_id, "dbkey": "hg19"}
        create_response = self._post(
            f"histories/{self.history_id}/contents/dataset_collections", create_data, json=True
        )
        collection = self.__check_create_collection_response(create_response)
        new_forward = collection["elements"][0]["object"]
        assert new_forward["metadata_dbkey"] == "hg19"
        assert new_forward["genome_build"] == "hg19"

    def test_hdca_copy_and_elements(self):
        hdca = self.dataset_collection_populator.create_pair_in_history(self.history_id, wait=True).json()["outputs"][0]
        hdca_id = hdca["id"]
        second_history_id = self.dataset_populator.new_history()
        create_data = dict(
            source="hdca",
            content=hdca_id,
            copy_elements=True,
        )
        assert len(self._get(f"histories/{second_history_id}/contents/dataset_collections").json()) == 0
        create_response = self._post(
            f"histories/{second_history_id}/contents/dataset_collections", create_data, json=True
        )
        self.__check_create_collection_response(create_response)

        contents = self._get(f"histories/{second_history_id}/contents/dataset_collections").json()
        assert len(contents) == 1
        new_forward, _ = self.__get_paired_response_elements(contents[0])
        self._assert_has_keys(new_forward, "history_id")
        assert new_forward["history_id"] == second_history_id

    def __get_paired_response_elements(self, contents):
        hdca = self.__show(contents).json()
        self._assert_has_keys(hdca, "name", "deleted", "visible", "elements")
        elements = hdca["elements"]
        assert len(elements) == 2
        element0 = elements[0]
        element1 = elements[1]
        self._assert_has_keys(element0, "object")
        self._assert_has_keys(element1, "object")

        return element0["object"], element1["object"]

    def test_hdca_from_library_datasets(self):
        ld = self.library_populator.new_library_dataset("el1")
        ldda_id = ld["ldda_id"]
        element_identifiers = [{"name": "el1", "src": "ldda", "id": ldda_id}]
        history_id = self.dataset_populator.new_history()
        create_data = dict(
            history_id=history_id,
            type="dataset_collection",
            name="Test From Library",
            element_identifiers=element_identifiers,
            collection_type="list",
        )
        create_response = self._post(f"histories/{history_id}/contents/dataset_collections", create_data, json=True)
        hdca = self.__check_create_collection_response(create_response)
        elements = hdca["elements"]
        assert len(elements) == 1
        hda = elements[0]["object"]
        assert hda["hda_ldda"] == "hda"
        assert hda["history_content_type"] == "dataset"
        assert hda["copied_from_ldda_id"] == ldda_id
        assert hda["history_id"] == history_id

    def test_hdca_from_inaccessible_library_datasets(self):
        library, library_dataset = self.library_populator.new_library_dataset_in_private_library(
            "HDCACreateInaccesibleLibrary"
        )
        ldda_id = library_dataset["id"]
        element_identifiers = [{"name": "el1", "src": "ldda", "id": ldda_id}]
        create_data = dict(
            history_id=self.history_id,
            type="dataset_collection",
            name="Test From Library",
            element_identifiers=element_identifiers,
            collection_type="list",
        )
        with self._different_user():
            second_history_id = self.dataset_populator.new_history()
            create_response = self._post(
                f"histories/{second_history_id}/contents/dataset_collections", create_data, json=True
            )
            self._assert_status_code_is(create_response, 403)

    def __check_create_collection_response(self, response):
        self._assert_status_code_is(response, 200)
        dataset_collection = response.json()
        if "output_collections" in dataset_collection:
            dataset_collection = dataset_collection["output_collections"][0]
        self._assert_has_keys(dataset_collection, "url", "name", "deleted", "visible", "elements")
        return dataset_collection

    def __show(self, contents):
        show_response = self._get(
            f"histories/{self.history_id}/contents/{contents['history_content_type']}s/{contents['id']}"
        )
        return show_response

    def __count_contents(self, history_id=None, **kwds):
        if history_id is None:
            history_id = self.history_id
        contents_response = self._get(f"histories/{history_id}/contents", kwds)
        return len(contents_response.json())

    def __assert_hda_has_full_details(self, hda_details):
        self._assert_has_keys(hda_details, "display_types", "display_apps")

    def __check_for_hda(self, contents_response, hda):
        self._assert_status_code_is(contents_response, 200)
        contents = contents_response.json()
        assert len(contents) == 1
        hda_summary = contents[0]
        self.__assert_matches_hda(hda, hda_summary)
        return hda_summary

    def __assert_matches_hda(self, input_hda, query_hda):
        self._assert_has_keys(query_hda, "id", "name")
        assert input_hda["name"] == query_hda["name"]
        assert input_hda["id"] == query_hda["id"]

    def test_job_state_summary_field(self):
        create_response = self.dataset_collection_populator.create_pair_in_history(
            self.history_id,
            contents=["123", "456"],
        )
        self._assert_status_code_is(create_response, 200)
        contents_response = self._get(f"histories/{self.history_id}/contents?v=dev&keys=job_state_summary&view=summary")
        self._assert_status_code_is(contents_response, 200)
        contents = contents_response.json()
        for c in contents:
            if c["history_content_type"] == "dataset_collection":
                assert isinstance(c, dict)
                assert "job_state_summary" in c
                assert isinstance(c["job_state_summary"], dict)

    def _get_content(self, history_id, update_time):
        return self._get(f"/api/histories/{history_id}/contents/near/100/100?update_time-gt={update_time}").json()

    def test_history_contents_near_with_update_time(self):
        with self.dataset_populator.test_history() as history_id:
            first_time = datetime.utcnow().isoformat()
            assert len(self._get_content(history_id, update_time=first_time)) == 0
            self.dataset_collection_populator.create_list_in_history(history_id=history_id, wait=True)
            assert len(self._get_content(history_id, update_time=first_time)) == 4  # 3 datasets
            self.dataset_populator.wait_for_history(history_id)
            all_datasets_finished = first_time = datetime.utcnow().isoformat()
            assert len(self._get_content(history_id, update_time=all_datasets_finished)) == 0

    def test_history_contents_near_with_since(self):
        with self.dataset_populator.test_history() as history_id:
            original_history = self._get(f"/api/histories/{history_id}").json()
            original_history_stamp = original_history["update_time"]

            # check empty contents, with no since flag, should return an empty 200 result
            history_contents = self._get(f"/api/histories/{history_id}/contents/near/100/100")
            assert history_contents.status_code == 200
            assert len(history_contents.json()) == 0

            # adding a since parameter, should return a 204 if history has not changed at all
            history_contents = self._get(
                f"/api/histories/{history_id}/contents/near/100/100?since={original_history_stamp}"
            )
            assert history_contents.status_code == 204

            # add some stuff
            self.dataset_collection_populator.create_list_in_history(history_id=history_id, wait=True)
            self.dataset_populator.wait_for_history(history_id)

            # check to make sure the added stuff is there
            changed_history_contents = self._get(f"/api/histories/{history_id}/contents/near/100/100")
            assert changed_history_contents.status_code == 200
            assert len(changed_history_contents.json()) == 4

            # check to make sure the history date has actually changed due to changing the contents
            changed_history = self._get(f"/api/histories/{history_id}").json()
            changed_history_stamp = changed_history["update_time"]
            assert original_history_stamp != changed_history_stamp

            # a repeated contents request with since=original_history_stamp should now return data
            # because we have added datasets and the update_time should have been changed
            changed_content = self._get(
                f"/api/histories/{history_id}/contents/near/100/100?since={original_history_stamp}"
            )
            assert changed_content.status_code == 200
            assert len(changed_content.json()) == 4

    def test_history_contents_near_since_with_standard_iso8601_date(self):
        with self.dataset_populator.test_history() as history_id:
            original_history = self._get(f"/api/histories/{history_id}").json()
            original_history_stamp = original_history["update_time"]

            # this is the standard date format that javascript will emit using .toISOString(), it
            # should be the expected date format for any modern api
            # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/toISOString

            # checking to make sure that the same exact history.update_time returns a "not changed"
            # result after date parsing
            valid_iso8601_date = original_history_stamp + "Z"
            encoded_valid_date = urllib.parse.quote_plus(valid_iso8601_date)
            history_contents = self._get(
                f"/api/histories/{history_id}/contents/near/100/100?since={encoded_valid_date}"
            )
            assert history_contents.status_code == 204

            # test parsing for other standard is08601 formats
            sample_formats = ["2021-08-26T15:53:02+00:00", "2021-08-26T15:53:02Z", "2002-10-10T12:00:00-05:00"]
            for date_str in sample_formats:
                encoded_date = urllib.parse.quote_plus(date_str)  # handles pluses, minuses
                history_contents = self._get(f"/api/histories/{history_id}/contents/near/100/100?since={encoded_date}")
                self._assert_status_code_is_ok(history_contents)

    @skip_without_tool("cat_data_and_sleep")
    def test_history_contents_near_with_update_time_implicit_collection(self):
        with self.dataset_populator.test_history() as history_id:
            fetch_response = self.dataset_collection_populator.create_list_in_history(history_id=history_id).json()
            hdca_id = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)["id"]
            self.dataset_populator.wait_for_history(history_id)
            inputs = {
                "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
                "sleep_time": 2,
            }
            response = self.dataset_populator.run_tool(
                "cat_data_and_sleep",
                inputs,
                history_id,
            )
            update_time = datetime.utcnow().isoformat()
            collection_id = response["implicit_collections"][0]["id"]
            for _ in range(20):
                time.sleep(1)
                update = self._get_content(history_id, update_time=update_time)
                if any(
                    c
                    for c in update
                    if c["history_content_type"] == "dataset_collection" and c["job_state_summary"]["ok"] == 3
                ):
                    return
            raise Exception(
                f"History content update time query did not include final update for implicit collection {collection_id}"
            )

    @skip_without_tool("collection_creates_dynamic_nested")
    def test_history_contents_near_with_update_time_explicit_collection(self):
        with self.dataset_populator.test_history() as history_id:
            inputs = {"foo": "bar", "sleep_time": 2}
            response = self.dataset_populator.run_tool(
                "collection_creates_dynamic_nested",
                inputs,
                history_id,
            )
            update_time = datetime.utcnow().isoformat()
            collection_id = response["output_collections"][0]["id"]
            for _ in range(20):
                time.sleep(1)
                update = self._get_content(history_id, update_time=update_time)
                if any(
                    c
                    for c in update
                    if c["history_content_type"] == "dataset_collection" and c["populated_state"] == "ok"
                ):
                    return
            raise Exception(
                f"History content update time query did not include populated_state update for dynamic nested collection {collection_id}"
            )

    def test_index_filter_by_type(self):
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.new_dataset(history_id)
        self.dataset_collection_populator.create_list_in_history(history_id=history_id, wait=True)

        contents_response = self._get(f"histories/{history_id}/contents").json()
        num_items = len(contents_response)
        expected_num_collections = 1
        expected_num_datasets = num_items - expected_num_collections

        contents_response = self._get(f"histories/{history_id}/contents?types=dataset").json()
        assert len(contents_response) == expected_num_datasets
        contents_response = self._get(f"histories/{history_id}/contents?types=dataset_collection").json()
        assert len(contents_response) == expected_num_collections
        contents_response = self._get(f"histories/{history_id}/contents?types=dataset,dataset_collection").json()
        assert len(contents_response) == expected_num_datasets + expected_num_collections
        contents_response = self._get(f"histories/{history_id}/contents?types=dataset&types=dataset_collection").json()
        assert len(contents_response) == expected_num_datasets + expected_num_collections

    def test_elements_datatypes_field(self):
        history_id = self.dataset_populator.new_history()
        collection_name = "homogeneous"
        expected_datatypes = ["txt"]
        elements = [  # List with all elements of txt datatype (homogeneous)
            {"name": "test1", "src": "pasted", "paste_content": "abc", "ext": "txt"},
            {"name": "test2", "src": "pasted", "paste_content": "abc", "ext": "txt"},
        ]
        self._upload_collection_list_with_elements(history_id, collection_name, elements)
        self._assert_collection_has_expected_elements_datatypes(history_id, collection_name, expected_datatypes)

        collection_name = "heterogeneous"
        expected_datatypes = ["txt", "tabular"]
        elements = [  # List with txt and tabular datatype (heterogeneous)
            {"name": "test2", "src": "pasted", "paste_content": "abc", "ext": "txt"},
            {"name": "test3", "src": "pasted", "paste_content": "a,b,c\n", "ext": "tabular"},
        ]
        self._upload_collection_list_with_elements(history_id, collection_name, elements)
        self._assert_collection_has_expected_elements_datatypes(history_id, collection_name, expected_datatypes)

    def _upload_collection_list_with_elements(self, history_id: str, collection_name: str, elements: List[Any]):
        create_homogeneous_response = self.dataset_collection_populator.upload_collection(
            history_id, "list", elements=elements, name=collection_name, wait=True
        )
        self._assert_status_code_is_ok(create_homogeneous_response)

    def _assert_collection_has_expected_elements_datatypes(self, history_id, collection_name, expected_datatypes):
        contents_response = self._get(
            f"histories/{history_id}/contents?v=dev&view=detailed&q=name-eq&qv={collection_name}"
        )
        self._assert_status_code_is(contents_response, 200)
        collection = contents_response.json()[0]
        self.assertCountEqual(collection["elements_datatypes"], expected_datatypes)


class HistoryContentsApiNearTestCase(ApiTestCase):
    """
    Test the /api/histories/{history_id}/contents/{direction}/{hid}/{limit} endpoint.
    """

    NEAR = DirectionOptions.near
    BEFORE = DirectionOptions.before
    AFTER = DirectionOptions.after

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def _create_list_in_history(self, history_id, n=2):
        # Creates list of size n*4 (n collections with 3 items each)
        for _ in range(n):
            self.dataset_collection_populator.create_list_in_history(history_id=history_id, wait=True)

    def _get_content(self, history_id, direction, *, hid, limit=1000):
        return self._get(f"/api/histories/{history_id}/contents/{direction}/{hid}/{limit}").json()

    def test_returned_hid_sequence_in_base_case(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id)
            result = self._get_content(history_id, self.NEAR, hid=1)
            assert len(result) == 8
            assert result[0]["hid"] == 8
            assert result[1]["hid"] == 7
            assert result[2]["hid"] == 6
            assert result[3]["hid"] == 5
            assert result[4]["hid"] == 4
            assert result[5]["hid"] == 3
            assert result[6]["hid"] == 2
            assert result[7]["hid"] == 1

    def test_near_even_limit(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id)
            result = self._get_content(history_id, self.NEAR, hid=5, limit=3)
            assert len(result) == 3
            assert result[0]["hid"] == 6  # hid + 1
            assert result[1]["hid"] == 5  # hid
            assert result[2]["hid"] == 4  # hid - 1

    def test_near_odd_limit(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id)
            result = self._get_content(history_id, self.NEAR, hid=5, limit=4)
            assert len(result) == 4
            assert result[0]["hid"] == 7  # hid + 2
            assert result[1]["hid"] == 6  # hid + 1
            assert result[2]["hid"] == 5  # hid
            assert result[3]["hid"] == 4  # hid - 1

    def test_near_less_than_before_limit(self):  # n before < limit // 2
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id)
            result = self._get_content(history_id, self.NEAR, hid=1, limit=3)
            assert len(result) == 2
            assert result[0]["hid"] == 2  # hid + 1
            assert result[1]["hid"] == 1  # hid (there's nothing before hid=1)

    def test_near_less_than_after_limit(self):  # n after < limit // 2 + 1
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id)
            result = self._get_content(history_id, self.NEAR, hid=8, limit=3)
            assert len(result) == 2
            assert result[0]["hid"] == 8  # hid (there's nothing after hid=8)
            assert result[1]["hid"] == 7  # hid - 1

    def test_near_less_than_before_and_after_limit(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id, n=1)
            result = self._get_content(history_id, self.NEAR, hid=2, limit=10)
            assert len(result) == 4
            assert result[0]["hid"] == 4  # hid + 2  (can't go after hid=4)
            assert result[1]["hid"] == 3  # hid + 1
            assert result[2]["hid"] == 2  # hid
            assert result[3]["hid"] == 1  # hid - 1  (can't go before hid=1)

    def test_before(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id)
            result = self._get_content(history_id, self.BEFORE, hid=5, limit=3)
            assert len(result) == 3
            assert result[0]["hid"] == 4  # hid - 1
            assert result[1]["hid"] == 3  # hid - 2
            assert result[2]["hid"] == 2  # hid - 3

    def test_before_less_than_limit(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id)
            result = self._get_content(history_id, self.BEFORE, hid=2, limit=3)
            assert len(result) == 1
            assert result[0]["hid"] == 1  # hid - 1

    def test_after(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id)
            result = self._get_content(history_id, self.AFTER, hid=5, limit=2)
            assert len(result) == 2
            assert result[0]["hid"] == 7  # hid + 2 (hid + 3 not included: tests reversed order)
            assert result[1]["hid"] == 6  # hid + 1

    def test_after_less_than_limit(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_list_in_history(history_id)
            result = self._get_content(history_id, self.AFTER, hid=7, limit=3)
            assert len(result) == 1
            assert result[0]["hid"] == 8  # hid + 1


class HistoryContentsApiBulkOperationTestCase(ApiTestCase):
    """
    Test the `/api/histories/{history_id}/contents/bulk` endpoint and the new
    `count` special view for `/api/histories/{history_id}/contents?v=dev`
    """

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_explicit_items_selection(self):
        with self.dataset_populator.test_history() as history_id:
            datasets_ids, collection_ids, history_contents = self._create_test_history_contents(history_id)

            # Hide 2 collections and 3 datasets, 5 in total
            payload = {
                "operation": "hide",
                "items": [
                    {
                        "id": datasets_ids[0],
                        "history_content_type": "dataset",
                    },
                    {
                        "id": collection_ids[0],
                        "history_content_type": "dataset_collection",
                    },
                    {
                        "id": datasets_ids[1],
                        "history_content_type": "dataset",
                    },
                    {
                        "id": collection_ids[1],
                        "history_content_type": "dataset_collection",
                    },
                    {
                        "id": datasets_ids[2],
                        "history_content_type": "dataset",
                    },
                ],
            }
            expected_hidden_item_ids = list(map(lambda item: item["id"], payload["items"]))
            expected_hidden_item_count = len(expected_hidden_item_ids)
            bulk_operation_result = self._apply_bulk_operation(history_id, payload)
            history_contents = self._get_history_contents(history_id)
            hidden_items = self._get_hidden_items_from_history_contents(history_contents)

            self._assert_bulk_success(bulk_operation_result, expected_hidden_item_count)
            assert len(hidden_items) == expected_hidden_item_count
            for item in hidden_items:
                assert item["id"] in expected_hidden_item_ids

    def test_dynamic_query_selection(self):
        with self.dataset_populator.test_history() as history_id:
            _, collection_ids, history_contents = self._create_test_history_contents(history_id)

            # Hide all collections using query
            payload = {"operation": "hide"}
            query = "q=history_content_type-eq&qv=dataset_collection"
            bulk_operation_result = self._apply_bulk_operation(history_id, payload, query)
            history_contents = self._get_history_contents(history_id)
            hidden_items = self._get_hidden_items_from_history_contents(history_contents)

            self._assert_bulk_success(bulk_operation_result, len(collection_ids))
            assert len(hidden_items) == len(collection_ids)
            for item in hidden_items:
                assert item["id"] in collection_ids

    def test_bulk_operations(self):
        with self.dataset_populator.test_history() as history_id:
            datasets_ids, collection_ids, history_contents = self._create_test_history_contents(history_id)

            # Hide all datasets using query
            payload = {"operation": "hide"}
            query = "q=history_content_type-eq&qv=dataset"
            bulk_operation_result = self._apply_bulk_operation(history_id, payload, query)
            history_contents = self._get_history_contents(history_id)
            hidden_items = self._get_hidden_items_from_history_contents(history_contents)
            self._assert_bulk_success(bulk_operation_result, len(datasets_ids))
            assert len(hidden_items) == len(datasets_ids)

            # Unhide datasets_ids[0] and datasets_ids[3]
            payload = {
                "operation": "unhide",
                "items": [
                    {
                        "id": datasets_ids[0],
                        "history_content_type": "dataset",
                    },
                    {
                        "id": datasets_ids[3],
                        "history_content_type": "dataset",
                    },
                ],
            }
            expected_unhidden_count = len(payload["items"])
            bulk_operation_result = self._apply_bulk_operation(history_id, payload)
            history_contents = self._get_history_contents(history_id)
            self._assert_bulk_success(bulk_operation_result, expected_unhidden_count)
            for item in history_contents:
                if item["id"] in [datasets_ids[0], datasets_ids[3]]:
                    assert item["visible"] is True

            # Delete all hidden datasets (total dataset - 2 previously unhidden)
            expected_hidden_item_count = len(datasets_ids) - expected_unhidden_count
            payload = {"operation": "delete"}
            query = "q=history_content_type-eq&qv=dataset&q=visible&qv=False"
            bulk_operation_result = self._apply_bulk_operation(history_id, payload, query)
            history_contents = self._get_history_contents(history_id)
            hidden_items = self._get_hidden_items_from_history_contents(history_contents)
            self._assert_bulk_success(bulk_operation_result, expected_hidden_item_count)
            for item in hidden_items:
                assert item["deleted"] is True

            # Undelete all items in history
            payload = {
                "operation": "undelete",
            }
            bulk_operation_result = self._apply_bulk_operation(history_id, payload)
            history_contents = self._get_history_contents(history_id)
            self._assert_bulk_success(bulk_operation_result, len(history_contents))
            for item in history_contents:
                assert item["deleted"] is False

            # Purge datasets_ids[0] and collection_ids[0]
            payload = {
                "operation": "purge",
                "items": [
                    {
                        "id": datasets_ids[0],
                        "history_content_type": "dataset",
                    },
                    {
                        "id": collection_ids[0],
                        "history_content_type": "dataset_collection",
                    },
                ],
            }
            expected_purged_count = len(payload["items"])
            bulk_operation_result = self._apply_bulk_operation(history_id, payload)
            history_contents = self._get_history_contents(history_id)
            self._assert_bulk_success(bulk_operation_result, expected_purged_count)
            purged_dataset = self._get_dataset_with_id_from_history_contents(history_contents, datasets_ids[0])
            assert purged_dataset["deleted"] is True
            assert purged_dataset["purged"] is True
            purged_collection = self._get_collection_with_id_from_history_contents(history_contents, collection_ids[0])
            # collections don't have a `purged` attribute but they should be marked deleted on purge
            assert purged_collection["deleted"] is True

            # Un-deleting a purged dataset should not have any effect
            payload = {
                "operation": "undelete",
                "items": [
                    {
                        "id": datasets_ids[0],
                        "history_content_type": "dataset",
                    },
                ],
            }
            bulk_operation_result = self._apply_bulk_operation(history_id, payload)
            history_contents = self._get_history_contents(history_id)
            self._assert_bulk_success(bulk_operation_result, 1)
            purged_dataset = self._get_dataset_with_id_from_history_contents(history_contents, datasets_ids[0])
            assert purged_dataset["deleted"] is True
            assert purged_dataset["purged"] is True

    def test_purging_collection_should_purge_contents(self):
        with self.dataset_populator.test_history() as history_id:
            datasets_ids, collection_ids, history_contents = self._create_test_history_contents(history_id)

            # Purge all collections
            payload = {"operation": "purge"}
            query = "q=history_content_type-eq&qv=dataset_collection"
            bulk_operation_result = self._apply_bulk_operation(history_id, payload, query)
            history_contents = self._get_history_contents(history_id)
            self._assert_bulk_success(bulk_operation_result, len(collection_ids))
            for item in history_contents:
                assert item["deleted"] is True
                if item["history_content_type"] == "dataset":
                    assert item["purged"] is True

    def test_only_owner_can_apply_bulk_operations(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_test_history_contents(history_id)

            with self._different_user():
                payload = {"operation": "hide"}
                bulk_operation_result = self._apply_bulk_operation(history_id, payload, expected_status_code=403)
                assert bulk_operation_result["err_msg"]

    def test_index_returns_expected_total_matches(self):
        with self.dataset_populator.test_history() as history_id:
            datasets_ids, collection_ids, history_contents = self._create_test_history_contents(history_id)

            self._test_index_total_matches(history_id, expected_total_matches=len(history_contents))

            self._test_index_total_matches(
                history_id,
                search_query="&q=history_content_type-eq&qv=dataset_collection",
                expected_total_matches=len(collection_ids),
            )

            self._test_index_total_matches(
                history_id,
                search_query="&q=history_content_type-eq&qv=dataset",
                expected_total_matches=len(datasets_ids),
            )

    def test_index_with_stats_fails_with_non_orm_filters(self):
        with self.dataset_populator.test_history() as history_id:
            self._create_test_history_contents(history_id)

            invalid_filter_keys_with_stats = ["genome_build", "data_type", "annotation"]

            for filter_key in invalid_filter_keys_with_stats:
                response = self._get_contents_with_stats(
                    history_id,
                    search_query=f"&q={filter_key}-contains&qv=anything",
                )
                self._assert_status_code_is(response, 400)

    def test_index_with_stats_has_extra_serialization(self):
        expected_extra_keys_in_collections = ["elements_datatypes"]
        with self.dataset_populator.test_history() as history_id:
            self._create_collection_in_history(history_id)
            response = self._get_contents_with_stats(
                history_id,
                search_query="&q=history_content_type-eq&qv=dataset_collection",
            )
            self._assert_status_code_is(response, 200)
            contents_with_stats = response.json()
            assert contents_with_stats["contents"]
            collection = contents_with_stats["contents"][0]
            self._assert_has_keys(collection, *expected_extra_keys_in_collections)

    def _get_contents_with_stats(self, history_id: str, search_query: str = ""):
        headers = {"accept": "application/vnd.galaxy.history.contents.stats+json"}
        search_response = self._get(f"histories/{history_id}/contents?v=dev{search_query}", headers=headers)
        return search_response

    def _test_index_total_matches(self, history_id: str, expected_total_matches: int, search_query: str = ""):
        search_response = self._get_contents_with_stats(history_id, search_query)
        self._assert_status_code_is(search_response, 200)
        self._assert_total_matches_is(search_response.json(), expected_total_matches)

    def _assert_total_matches_is(self, response, expected_total_matches: int):
        assert response["stats"]
        assert response["stats"]["total_matches"]
        assert response["stats"]["total_matches"] == expected_total_matches

    def _create_test_history_contents(self, history_id) -> Tuple[List[str], List[str], List[Any]]:
        """Creates 3 collections (pairs) and their corresponding datasets (6 in total)

        Returns a tuple with the list of ids for the datasets and the collections and the
        complete history contents
        """
        num_expected_collections = 3
        num_expected_datasets = num_expected_collections * 2
        collection_ids = self._create_collection_in_history(history_id, num_expected_collections)
        history_contents = self._get_history_contents(history_id)
        datasets = filter(lambda item: item["history_content_type"] == "dataset", history_contents)
        datasets_ids = list(map(lambda dataset: dataset["id"], datasets))
        assert len(history_contents) == num_expected_datasets + num_expected_collections
        assert len(datasets_ids) == num_expected_datasets
        for dataset_id in datasets_ids:
            self._put(f"histories/{history_id}/contents/{dataset_id}", {"visible": True}, json=True).json()
        # All items are visible
        history_contents = self._get_history_contents(history_id)
        for item in history_contents:
            assert item["visible"]
        return datasets_ids, collection_ids, history_contents

    def _create_collection_in_history(self, history_id, num_collections=1) -> List[str]:
        collection_ids = []
        for _ in range(num_collections):
            collection_id = self.dataset_collection_populator.create_pair_in_history(
                history_id=history_id, wait=True
            ).json()["outputs"][0]["id"]
            collection_ids.append(collection_id)
        return collection_ids

    def _get_history_contents(self, history_id: str):
        return self._get(f"histories/{history_id}/contents").json()

    def _get_hidden_items_from_history_contents(self, history_contents) -> List[Any]:
        return [content for content in history_contents if not content["visible"]]

    def _get_collection_with_id_from_history_contents(self, history_contents, collection_id: str) -> Optional[Any]:
        return self._get_item_with_id_from_history_contents(history_contents, "dataset_collection", collection_id)

    def _get_dataset_with_id_from_history_contents(self, history_contents, dataset_id: str) -> Optional[Any]:
        return self._get_item_with_id_from_history_contents(history_contents, "dataset", dataset_id)

    def _get_item_with_id_from_history_contents(
        self, history_contents, history_content_type: str, dataset_id: str
    ) -> Optional[Any]:
        for item in history_contents:
            if item["history_content_type"] == history_content_type and item["id"] == dataset_id:
                return item
        return None

    def _apply_bulk_operation(self, history_id: str, payload, query: str = "", expected_status_code: int = 200):
        if query:
            query = f"?{query}"
        response = self._put(
            f"histories/{history_id}/contents/bulk{query}",
            data=payload,
            json=True,
        )
        self._assert_status_code_is(response, expected_status_code)
        return response.json()

    def _assert_bulk_success(self, bulk_operation_result, expected_success_count: int):
        assert bulk_operation_result["success_count"] == expected_success_count, bulk_operation_result
        assert not bulk_operation_result["errors"]

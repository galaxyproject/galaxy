from typing import Optional

from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class TestGroupsApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_create_valid(self, group_name: Optional[str] = None):
        payload = self._build_valid_group_payload(group_name)
        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        group = response.json()[0]  # POST /api/groups returns a list
        self._assert_valid_group(group)
        return group

    def test_create_only_admin(self):
        response = self._post("groups", json=True)
        self._assert_status_code_is(response, 403)

    def test_create_invalid_params_raises_400(self):
        payload = self._build_valid_group_payload()
        payload["name"] = None
        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 400)

    def test_create_duplicated_name_raises_409(self):
        payload = self._build_valid_group_payload()
        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)

        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 409)

    def test_index(self):
        self.test_create_valid()
        response = self._get("groups", admin=True)
        self._assert_status_code_is(response, 200)
        groups = response.json()
        assert isinstance(groups, list)
        assert len(groups) > 0
        for group in groups:
            self._assert_valid_group(group)

    def test_index_only_admin(self):
        response = self._get("groups")
        self._assert_status_code_is(response, 403)

    def test_show(self):
        group = self.test_create_valid()
        group_id = group["id"]
        response = self._get(f"groups/{group_id}", admin=True)
        self._assert_status_code_is(response, 200)
        response_group = response.json()
        self._assert_valid_group(response_group)
        self._assert_has_keys(response_group, "users_url", "roles_url")

    def test_show_only_admin(self):
        group = self.test_create_valid()
        group_id = group["id"]
        response = self._get(f"groups/{group_id}")
        self._assert_status_code_is(response, 403)

    def test_show_unknown_raises_400(self):
        group_id = "invalid-group-id"
        response = self._get(f"groups/{group_id}", admin=True)
        self._assert_status_code_is(response, 400)

    def test_update(self):
        group = self.test_create_valid(group_name="group-test")

        group_id = group["id"]
        updated_name = "group-test-updated"
        update_payload = {
            "name": updated_name,
        }
        update_response = self._put(f"groups/{group_id}", data=update_payload, admin=True, json=True)
        self._assert_status_code_is_ok(update_response)

    def test_update_only_admin(self):
        group = self.test_create_valid()
        group_id = group["id"]
        response = self._put(f"groups/{group_id}")
        self._assert_status_code_is(response, 403)

    def test_update_duplicating_name_raises_409(self):
        group_a = self.test_create_valid()
        group_b = self.test_create_valid()

        # Update group_b with the same name as group_a
        group_b_id = group_b["id"]
        updated_name = group_a["name"]
        update_payload = {
            "name": updated_name,
        }
        update_response = self._put(f"groups/{group_b_id}", data=update_payload, admin=True, json=True)
        self._assert_status_code_is(update_response, 409)

    def _assert_valid_group(self, group, assert_id=None):
        self._assert_has_keys(group, "id", "name", "model_class", "url")
        if assert_id is not None:
            assert group["id"] == assert_id

    def _build_valid_group_payload(self, name: Optional[str] = None):
        name = name or self.dataset_populator.get_random_name()
        user_id = self.dataset_populator.user_id()
        role_id = self.dataset_populator.user_private_role_id()
        payload = {
            "name": name,
            "user_ids": [user_id],
            "role_ids": [role_id],
        }
        return payload

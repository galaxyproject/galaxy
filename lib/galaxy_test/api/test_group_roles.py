from typing import (
    List,
    Optional,
)

from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class GroupRolesApiTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_index(self, group_name: Optional[str] = None):
        group_name = group_name or "test-group_roles"
        group = self._create_group(group_name)
        encoded_group_id = group["id"]

        group_roles = self._get_group_roles(encoded_group_id)

        assert isinstance(group_roles, list)
        assert len(group_roles) > 0
        for group_role in group_roles:
            self._assert_valid_group_role(group_role)

    def test_index_only_admin(self):
        encoded_group_id = "any-group-id"
        response = self._get(f"groups/{encoded_group_id}/roles")
        self._assert_status_code_is(response, 403)

    def test_index_unknown_group_raises_400(self):
        encoded_group_id = "unknown-group-id"
        response = self._get(f"groups/{encoded_group_id}/roles", admin=True)
        self._assert_status_code_is(response, 400)

    def test_show(self):
        encoded_role_id = self.dataset_populator.user_private_role_id()
        group = self._create_group("test-group-show-role", encoded_role_ids=[encoded_role_id])
        encoded_group_id = group["id"]
        response = self._get(f"groups/{encoded_group_id}/roles/{encoded_role_id}", admin=True)
        self._assert_status_code_is(response, 200)
        group_role = response.json()
        self._assert_valid_group_role(group_role)

    def test_show_only_admin(self):
        encoded_group_id = "any-group-id"
        encoded_role_id = "any-role-id"
        response = self._get(f"groups/{encoded_group_id}/roles/{encoded_role_id}")
        self._assert_status_code_is(response, 403)

    def test_show_unknown_raises_400(self):
        group = self._create_group("test-group-with-unknown-role")
        encoded_group_id = group["id"]
        encoded_role_id = "unknown-role-id"
        response = self._get(f"groups/{encoded_group_id}/roles/{encoded_role_id}", admin=True)
        self._assert_status_code_is(response, 400)

    def test_update(self):
        group_name = "group-without-roles"
        group = self._create_group(group_name, encoded_role_ids=[])
        encoded_group_id = group["id"]

        group_roles = self._get_group_roles(encoded_group_id)
        assert len(group_roles) == 0

        encoded_role_id = self.dataset_populator.user_private_role_id()
        update_response = self._put(f"groups/{encoded_group_id}/roles/{encoded_role_id}", admin=True)
        self._assert_status_code_is_ok(update_response)
        group_role = update_response.json()
        self._assert_valid_group_role(group_role, assert_id=encoded_role_id)
        assert group_role["url"] == f"/api/groups/{encoded_group_id}/roles/{encoded_role_id}"

    def test_update_only_admin(self):
        encoded_group_id = "any-group-id"
        encoded_role_id = "any-role-id"
        response = self._put(f"groups/{encoded_group_id}/roles/{encoded_role_id}")
        self._assert_status_code_is(response, 403)

    def test_delete(self):
        group_name = "group-with-role-to-delete"
        encoded_role_id = self.dataset_populator.user_private_role_id()
        group = self._create_group(group_name, encoded_role_ids=[encoded_role_id])
        encoded_group_id = group["id"]

        group_roles = self._get_group_roles(encoded_group_id)
        assert len(group_roles) == 1

        delete_response = self._delete(f"groups/{encoded_group_id}/roles/{encoded_role_id}", admin=True)
        self._assert_status_code_is_ok(delete_response)
        group_role = delete_response.json()
        self._assert_valid_group_role(group_role, assert_id=encoded_role_id)

        group_roles = self._get_group_roles(encoded_group_id)
        assert len(group_roles) == 0

    def test_delete_only_admin(self):
        encoded_group_id = "any-group-id"
        encoded_role_id = "any-role-id"
        response = self._delete(f"groups/{encoded_group_id}/roles/{encoded_role_id}")
        self._assert_status_code_is(response, 403)

    def test_delete_unknown_raises_400(self):
        group_name = "group-without-role-to-delete"
        group = self._create_group(group_name, encoded_role_ids=[])
        encoded_group_id = group["id"]

        group_roles = self._get_group_roles(encoded_group_id)
        assert len(group_roles) == 0

        encoded_role_id = "unknown-role-id"
        delete_response = self._delete(f"groups/{encoded_group_id}/roles/{encoded_role_id}", admin=True)
        self._assert_status_code_is(delete_response, 400)

    def _create_group(self, group_name: str, encoded_role_ids: Optional[List[str]] = None):
        if encoded_role_ids is None:
            encoded_role_ids = [self.dataset_populator.user_private_role_id()]
        role_ids = encoded_role_ids
        payload = {
            "name": group_name,
            "role_ids": role_ids,
        }
        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        group = response.json()[0]  # POST /api/groups returns a list
        return group

    def _get_group_roles(self, encoded_group_id: str):
        response = self._get(f"groups/{encoded_group_id}/roles", admin=True)
        self._assert_status_code_is(response, 200)
        group_roles = response.json()
        return group_roles

    def _assert_valid_group_role(self, role, assert_id=None):
        self._assert_has_keys(role, "id", "name", "url")
        if assert_id is not None:
            assert role["id"] == assert_id

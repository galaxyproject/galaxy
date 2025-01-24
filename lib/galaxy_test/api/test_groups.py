from typing import (
    List,
    Optional,
)

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
        user_id = self.dataset_populator.user_id()
        user_private_role_id = self.dataset_populator.user_private_role_id()
        original_name = f"group-test-{self.dataset_populator.get_random_name()}"
        group = self.test_create_valid(group_name=original_name)

        self._assert_group_has_expected_values(
            group["id"],
            name=original_name,
            user_ids=[user_id],
            role_ids=[user_private_role_id],
        )

        group_id = group["id"]
        updated_name = f"group-test-updated-{self.dataset_populator.get_random_name()}"
        update_response = self._put(f"groups/{group_id}", data={"name": updated_name}, admin=True, json=True)
        self._assert_status_code_is_ok(update_response)

        # Only the name should be updated
        self._assert_group_has_expected_values(
            group_id,
            name=updated_name,
            user_ids=[user_id],
            role_ids=[user_private_role_id],
        )

        # Add another user to the group
        another_user_email = f"user-{self.dataset_populator.get_random_name()}@example.com"
        another_user_id = None
        with self._different_user(another_user_email):
            another_user_id = self.dataset_populator.user_id()
            another_role_id = self.dataset_populator.user_private_role_id()
        assert another_user_id is not None
        update_response = self._put(
            f"groups/{group_id}", data={"user_ids": [user_id, another_user_id]}, admin=True, json=True
        )
        self._assert_status_code_is_ok(update_response)

        # Check if the user was added
        self._assert_group_has_expected_values(
            group_id,
            name=updated_name,
            user_ids=[user_id, another_user_id],
            role_ids=[user_private_role_id],
        )

        # Add another role to the group
        update_response = self._put(
            f"groups/{group_id}", data={"role_ids": [user_private_role_id, another_role_id]}, admin=True, json=True
        )
        self._assert_status_code_is_ok(update_response)

        # Check if the role was added
        self._assert_group_has_expected_values(
            group_id,
            name=updated_name,
            user_ids=[user_id, another_user_id],
            role_ids=[user_private_role_id, another_role_id],
        )

        # TODO: Test removing users and roles
        # Currently not possible because the API can only add users and roles

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

    def test_delete(self):
        group = self.test_create_valid()
        group_id = group["id"]
        delete_response = self._delete(f"groups/{group_id}", admin=True)
        self._assert_status_code_is_ok(delete_response)

    def test_delete_duplicating_name_raises_409(self):
        group = self.test_create_valid()
        group_id = group["id"]
        group_name = group["name"]

        delete_response = self._delete(f"groups/{group_id}", admin=True)
        self._assert_status_code_is_ok(delete_response)

        # Create a new group with the same name as the deleted one is not allowed
        payload = self._build_valid_group_payload(group_name)
        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 409)

    def test_purge(self):
        group = self.test_create_valid()
        group_id = group["id"]

        # Delete and purge the group
        delete_response = self._delete(f"groups/{group_id}", admin=True)
        self._assert_status_code_is_ok(delete_response)
        purge_response = self._post(f"groups/{group_id}/purge", admin=True)
        self._assert_status_code_is_ok(purge_response)

        # The group is deleted and purged, so it cannot be found
        response = self._get(f"groups/{group_id}", admin=True)
        self._assert_status_code_is(response, 404)

    def test_purge_can_reuse_name(self):
        group = self.test_create_valid()
        group_id = group["id"]
        group_name = group["name"]

        # Delete and purge the group
        delete_response = self._delete(f"groups/{group_id}", admin=True)
        self._assert_status_code_is_ok(delete_response)
        purge_response = self._post(f"groups/{group_id}/purge", admin=True)
        self._assert_status_code_is_ok(purge_response)

        # Create a new group with the same name as the deleted one is allowed
        payload = self._build_valid_group_payload(group_name)
        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)

    def _assert_valid_group(self, group, assert_id=None):
        self._assert_has_keys(group, "id", "name", "model_class", "url")
        if assert_id is not None:
            assert group["id"] == assert_id

    def _assert_group_has_expected_values(self, group_id: str, name: str, user_ids: List[str], role_ids: List[str]):
        group = self._get(f"groups/{group_id}", admin=True).json()
        assert group["name"] == name
        users = self._get(f"groups/{group_id}/users", admin=True).json()
        assert len(users) == len(user_ids)
        for user in users:
            assert user["id"] in user_ids
        roles = self._get(f"groups/{group_id}/roles", admin=True).json()
        assert len(roles) == len(role_ids)
        for role in roles:
            assert role["id"] in role_ids

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

from typing import (
    List,
    Optional,
)

from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class GroupUsersApiTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_index(self, group_name: Optional[str] = None):
        group_name = group_name or "test-group_users"
        group = self._create_group(group_name)
        encoded_group_id = group["id"]

        group_users = self._get_group_users(encoded_group_id)

        assert isinstance(group_users, list)
        assert len(group_users) > 0
        for group_user in group_users:
            self._assert_valid_group_user(group_user)

    def test_index_only_admin(self):
        encoded_group_id = "any-group-id"
        response = self._get(f"groups/{encoded_group_id}/users")
        self._assert_status_code_is(response, 403)

    def test_index_unknown_group_raises_400(self):
        encoded_group_id = "unknown-group-id"
        response = self._get(f"groups/{encoded_group_id}/users", admin=True)
        self._assert_status_code_is(response, 400)

    def test_show(self):
        encoded_user_id = self.dataset_populator.user_id()
        group = self._create_group("test-group-show-user", encoded_user_ids=[encoded_user_id])
        encoded_group_id = group["id"]
        response = self._get(f"groups/{encoded_group_id}/users/{encoded_user_id}", admin=True)
        self._assert_status_code_is(response, 200)
        group_user = response.json()
        self._assert_valid_group_user(group_user)

    def test_show_only_admin(self):
        encoded_group_id = "any-group-id"
        encoded_user_id = "any-user-id"
        response = self._get(f"groups/{encoded_group_id}/users/{encoded_user_id}")
        self._assert_status_code_is(response, 403)

    def test_show_unknown_raises_400(self):
        group = self._create_group("test-group-with-unknown-user")
        encoded_group_id = group["id"]
        encoded_user_id = "unknown-user-id"
        response = self._get(f"groups/{encoded_group_id}/users/{encoded_user_id}", admin=True)
        self._assert_status_code_is(response, 400)

    def test_update(self):
        group_name = "group-without-users"
        group = self._create_group(group_name, encoded_user_ids=[])
        encoded_group_id = group["id"]

        group_users = self._get_group_users(encoded_group_id)
        assert len(group_users) == 0

        encoded_user_id = self.dataset_populator.user_id()
        update_response = self._put(f"groups/{encoded_group_id}/users/{encoded_user_id}", admin=True)
        self._assert_status_code_is_ok(update_response)
        group_user = update_response.json()
        self._assert_valid_group_user(group_user, assert_id=encoded_user_id)
        assert group_user["url"] == f"/api/groups/{encoded_group_id}/user/{encoded_user_id}"

    def test_update_only_admin(self):
        encoded_group_id = "any-group-id"
        encoded_user_id = "any-user-id"
        response = self._put(f"groups/{encoded_group_id}/users/{encoded_user_id}")
        self._assert_status_code_is(response, 403)

    def test_delete(self):
        group_name = "group-with-user-to-delete"
        encoded_user_id = self.dataset_populator.user_id()
        group = self._create_group(group_name, encoded_user_ids=[encoded_user_id])
        encoded_group_id = group["id"]

        group_users = self._get_group_users(encoded_group_id)
        assert len(group_users) == 1

        delete_response = self._delete(f"groups/{encoded_group_id}/users/{encoded_user_id}", admin=True)
        self._assert_status_code_is_ok(delete_response)
        group_user = delete_response.json()
        self._assert_valid_group_user(group_user, assert_id=encoded_user_id)

        group_users = self._get_group_users(encoded_group_id)
        assert len(group_users) == 0

    def test_delete_only_admin(self):
        encoded_group_id = "any-group-id"
        encoded_user_id = "any-user-id"
        response = self._delete(f"groups/{encoded_group_id}/users/{encoded_user_id}")
        self._assert_status_code_is(response, 403)

    def test_delete_unknown_raises_400(self):
        group_name = "group-without-user-to-delete"
        group = self._create_group(group_name, encoded_user_ids=[])
        encoded_group_id = group["id"]

        group_users = self._get_group_users(encoded_group_id)
        assert len(group_users) == 0

        encoded_user_id = "unknown-user-id"
        delete_response = self._delete(f"groups/{encoded_group_id}/users/{encoded_user_id}", admin=True)
        self._assert_status_code_is(delete_response, 400)

    def _create_group(self, group_name: str, encoded_user_ids: Optional[List[str]] = None):
        if encoded_user_ids is None:
            encoded_user_ids = [self.dataset_populator.user_id()]
        user_ids = encoded_user_ids
        payload = {
            "name": group_name,
            "user_ids": user_ids,
        }
        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        group = response.json()[0]  # POST /api/groups returns a list
        return group

    def _get_group_users(self, encoded_group_id: str):
        response = self._get(f"groups/{encoded_group_id}/users", admin=True)
        self._assert_status_code_is(response, 200)
        group_users = response.json()
        return group_users

    def _assert_valid_group_user(self, user, assert_id=None):
        self._assert_has_keys(user, "id", "email", "url")
        if assert_id is not None:
            assert user["id"] == assert_id

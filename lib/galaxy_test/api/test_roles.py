from typing import (
    Any,
    Dict,
    Optional,
)

from galaxy.exceptions import error_codes
from galaxy_test.base.api_asserts import (
    assert_error_code_is,
    assert_has_keys,
    assert_status_code_is,
)
from galaxy_test.base.decorators import requires_admin
from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class TestRolesApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @requires_admin
    def test_list_and_show(self):
        def check_roles_response(response):
            assert_status_code_is(response, 200)
            as_list = response.json()
            assert isinstance(as_list, list)
            assert len(as_list) > 0
            for role in as_list:
                self.check_role_dict(role)

        user_role_id = self.dataset_populator.user_private_role_id()
        with self._different_user():
            different_user_role_id = self.dataset_populator.user_private_role_id()

        admin_roles_response = self._get("roles", admin=True)
        user_roles_response = self._get("roles")

        check_roles_response(admin_roles_response)
        check_roles_response(user_roles_response)

        admin_roles_response_ids = [r["id"] for r in admin_roles_response.json()]
        user_roles_response_ids = [r["id"] for r in user_roles_response.json()]

        # User can see their own private role not the other users, admin can see both.
        assert user_role_id in user_roles_response_ids
        assert different_user_role_id not in user_roles_response_ids

        assert user_role_id in admin_roles_response_ids
        assert different_user_role_id in admin_roles_response_ids

        # Check showing a valid, role.
        role_response = self._get(f"roles/{user_role_id}")
        assert_status_code_is(role_response, 200)
        role = role_response.json()
        self.check_role_dict(role, assert_id=user_role_id)

    @requires_admin
    def test_create_invalid_params(self):
        # In theory these low-level validation test cases could be handled in more
        # of a unit test style but it makes sense during the transition from wsgi to
        # asgi to have some tests that validate the whole pipeline is being integrated
        # properly in terms of exception handling.

        # Test missing description
        name = self.dataset_populator.get_random_name()
        description = "A test role."
        payload = {
            "name": name,
            "user_ids": [self.dataset_populator.user_id()],
        }
        response = self._post("roles", payload, admin=True, json=True)
        assert_status_code_is(response, 400)
        assert_error_code_is(response, error_codes.error_codes_by_name["USER_REQUEST_MISSING_PARAMETER"].code)
        assert "description" in response.json()["err_msg"]

        # Test missing name
        payload_missing_name = {
            "description": description,
            "user_ids": [self.dataset_populator.user_id()],
        }
        response = self._post("roles", payload_missing_name, admin=True, json=True)
        assert_status_code_is(response, 400)
        assert_error_code_is(response, error_codes.error_codes_by_name["USER_REQUEST_MISSING_PARAMETER"].code)
        assert "name" in response.json()["err_msg"]

        # Test invalid type for name
        payload_invalid_type = {
            "name": ["a test", "name"],
            "description": description,
            "user_ids": [self.dataset_populator.user_id()],
        }
        response = self._post("roles", payload_invalid_type, admin=True, json=True)
        assert_status_code_is(response, 400)
        assert_error_code_is(response, error_codes.error_codes_by_name["USER_REQUEST_INVALID_PARAMETER"].code)
        assert "name" in response.json()["err_msg"]
        assert "validation_errors" in response.json()

    @requires_admin
    def test_create_valid(self):
        name = self.dataset_populator.get_random_name()
        description = "A test role."
        role = self._create_role(name=name, description=description)

        assert role["name"] == name
        assert role["description"] == description

        user_roles_response = self._get("roles")
        with self._different_user():
            different_user_roles_response = self._get("roles")

        user_roles_response_ids = [r["id"] for r in user_roles_response.json()]
        different_user_roles_response_ids = [r["id"] for r in different_user_roles_response.json()]

        # This new role is public, all users see it.
        assert role["id"] in user_roles_response_ids
        assert role["id"] in different_user_roles_response_ids

    @requires_admin
    def test_show_error_codes(self):
        # Bad role ids are 400.
        response = self._get("roles/badroleid")
        assert_status_code_is(response, 400)

        # Trying to access others roles raise (not found) error
        with self._different_user():
            different_user_role_id = self.dataset_populator.user_private_role_id()
        response = self._get(f"roles/{different_user_role_id}")
        assert_status_code_is(response, 404)

    @requires_admin
    def test_create_only_admin(self):
        response = self._post("roles", json=True)
        assert_status_code_is(response, 403)
        response_err = response.json()
        assert response_err["err_code"] == 403006
        assert "administrator" in response_err["err_msg"]

    @requires_admin
    def test_delete(self):
        role = self._create_role()
        role_id = role["id"]
        response = self._delete(f"roles/{role_id}", admin=True)
        assert_status_code_is(response, 200)

    @requires_admin
    def test_delete_duplicating_name_raises_409(self):
        role = self._create_role()
        role_id = role["id"]
        role_name = role["name"]

        delete_response = self._delete(f"roles/{role_id}", admin=True)
        self._assert_status_code_is_ok(delete_response)

        # Create a new role with the same name as the deleted one is not allowed
        payload = self._build_valid_role_payload(role_name)
        response = self._post("roles", payload, admin=True, json=True)
        self._assert_status_code_is(response, 409)

    @requires_admin
    def test_purge(self):
        role = self._create_role()
        role_id = role["id"]

        # Delete and purge the role
        delete_response = self._delete(f"roles/{role_id}", admin=True)
        self._assert_status_code_is_ok(delete_response)
        purge_response = self._post(f"roles/{role_id}/purge", admin=True)
        self._assert_status_code_is_ok(purge_response)

        # The role is deleted and purged, so it cannot be found
        response = self._get(f"roles/{role_id}", admin=True)
        self._assert_status_code_is(response, 404)

    @requires_admin
    def test_purge_can_reuse_name(self):
        role = self._create_role()
        role_id = role["id"]
        role_name = role["name"]

        # Delete and purge the role
        delete_response = self._delete(f"roles/{role_id}", admin=True)
        self._assert_status_code_is_ok(delete_response)
        purge_response = self._post(f"roles/{role_id}/purge", admin=True)
        self._assert_status_code_is_ok(purge_response)

        # Create a new role with the same name as the deleted one is allowed
        payload = self._build_valid_role_payload(role_name)
        response = self._post("roles", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)

    def _create_role(self, name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        payload = self._build_valid_role_payload(name=name, description=description)
        response = self._post("roles", payload, admin=True, json=True)
        assert_status_code_is(response, 200)
        role = response.json()
        self.check_role_dict(role)
        return role

    def _build_valid_role_payload(self, name: Optional[str] = None, description: Optional[str] = None):
        name = name or self.dataset_populator.get_random_name()
        description = description or f"A test role with name: {name}."
        payload = {
            "name": name,
            "description": description,
            "user_ids": [self.dataset_populator.user_id()],
        }
        return payload

    @staticmethod
    def check_role_dict(role_dict: Dict[str, Any], assert_id: Optional[str] = None) -> None:
        assert_has_keys(role_dict, "id", "name", "model_class", "url")
        assert role_dict["model_class"] == "Role"
        if assert_id is not None:
            assert role_dict["id"] == assert_id

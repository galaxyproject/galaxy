import json
from typing import Any
from unittest import SkipTest

from galaxy_test.base.api import UsesApiTestCaseMixin


class SharingApiTests(UsesApiTestCaseMixin):
    """ Includes some tests for the sharing functionality of a particular resource type."""

    # The api_name has to be set to the appropriate value in the class using these tests.
    api_name: str

    def create(self, name: str) -> str:
        """Creates a shareable resource with the given name and returns it's ID.

        :param name: The name of the shareable resource to create.
        :return: The ID of the resource.
        """
        raise SkipTest("Abstract")

    def test_sharing_get_status(self):
        resource_id = self.create("resource-to-share")
        sharing_response = self._get_resource_sharing_status(resource_id)
        self._assert_has_keys(sharing_response, "title", "importable", "id", "username_and_slug", "published", "users_shared_with")

    def test_sharing_access(self):
        resource_id = self.create("resource-to-enable-link-access")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert sharing_response["importable"] is False

        payload = {"action": "enable_link_access"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is True

        payload = {"action": "disable_link_access"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is False

    def test_sharing_publish(self):
        resource_id = self.create("resource-to-publish")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert sharing_response["importable"] is False
        assert sharing_response["published"] is False

        payload = {"action": "publish"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is True
        assert sharing_response["published"] is True

        payload = {"action": "unpublish"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is True
        assert sharing_response["published"] is False

    def test_sharing_with_user_id(self):
        target_user = self._setup_user("target@user.com")
        target_user_id = target_user["id"]

        resource_id = self.create("resource-to-share-user-id")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert not sharing_response["users_shared_with"]

        payload = {"action": "share_with", "user_ids": [target_user_id]}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["users_shared_with"]
        assert sharing_response["users_shared_with"][0]["id"] == target_user_id

        payload = {"action": "unshare_with", "user_ids": [target_user_id]}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert not sharing_response["users_shared_with"]

    def test_sharing_with_user_email(self):
        target_user = self._setup_user("target@user.com")
        target_user_email = target_user["email"]

        resource_id = self.create("resource-to-share-user-email")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert not sharing_response["users_shared_with"]

        payload = {"action": "share_with", "user_ids": [target_user_email]}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["users_shared_with"]
        assert sharing_response["users_shared_with"][0]["email"] == target_user_email

        payload = {"action": "unshare_with", "user_ids": [target_user_email]}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert not sharing_response["users_shared_with"]

    def test_sharing_with_invalid_user(self):
        invalid_user_email = "unknown@user.com"

        resource_id = self.create("resource-to-share-user-unknown")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert not sharing_response["users_shared_with"]

        payload = {"action": "share_with", "user_ids": [invalid_user_email]}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert not sharing_response["users_shared_with"]
        assert invalid_user_email in sharing_response["share_with_err"]

    def test_set_slug(self):
        resource_id = self.create("resource-to-set-slug")
        other_resource_id = self.create("other-resource-to-set-slug")

        response = self._set_slug(resource_id, "new-slug")
        self._assert_status_code_is_ok(response)

        # Slugs must be unique for the same user/resource
        response = self._set_slug(other_resource_id, "new-slug")
        self._assert_status_code_is(response, 409)

        # Other users can not change the slug if they don't own the resource
        with self._different_user():
            response = self._set_slug(resource_id, "another-slug")
            self._assert_status_code_is(response, 403)

    def _get_resource_sharing_status(self, resource_id: str):
        sharing_response = self._get(f"{self.api_name}/{resource_id}/sharing")
        self._assert_status_code_is(sharing_response, 200)
        return sharing_response.json()

    def _set_resource_sharing(self, resource_id: str, payload: Any, expect_response_status: int = 200):
        sharing_response = self._post(f"{self.api_name}/{resource_id}/sharing", data=payload, json=True)
        self._assert_status_code_is(sharing_response, expect_response_status)
        return sharing_response.json()

    def _set_slug(self, resource_id: str, new_slug: str):
        payload = {"new_slug": new_slug}
        response = self._put(f"{self.api_name}/{resource_id}/slug", json.dumps(payload))
        return response

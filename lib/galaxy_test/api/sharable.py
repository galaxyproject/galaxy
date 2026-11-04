from typing import (
    Any,
)
from unittest import SkipTest
from uuid import uuid4

from galaxy.exceptions import error_codes
from galaxy_test.base.api import UsesApiTestCaseMixin


class SharingApiTests(UsesApiTestCaseMixin):
    """Includes some tests for the sharing functionality of a particular resource type."""

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
        self._assert_has_keys(
            sharing_response, "title", "importable", "id", "username_and_slug", "published", "users_shared_with"
        )

    def test_sharing_access(self):
        resource_id = self.create("resource-to-enable-link-access")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert sharing_response["importable"] is False

        sharing_response = self._set_resource_sharing(resource_id, "enable_link_access")
        assert sharing_response["importable"] is True

        sharing_response = self._set_resource_sharing(resource_id, "disable_link_access")
        assert sharing_response["importable"] is False

    def test_sharing_publish(self):
        resource_id = self.create("resource-to-publish")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert sharing_response["importable"] is False
        assert sharing_response["published"] is False

        sharing_response = self._set_resource_sharing(resource_id, "publish")
        assert sharing_response["importable"] is True
        assert sharing_response["published"] is True

        sharing_response = self._set_resource_sharing(resource_id, "unpublish")
        assert sharing_response["importable"] is True
        assert sharing_response["published"] is False

    def test_sharing_without_user(self):
        resource_id = self.create("resource-to-share-with-empty")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert not sharing_response["users_shared_with"]

        payload: dict[str, list[str]] = {"user_ids": []}
        sharing_response = self._set_resource_sharing(resource_id, action="share_with_users", payload=payload)
        assert not sharing_response["users_shared_with"]

    def test_sharing_with_user_id(self):
        target_user = self._setup_user("target@user.com")
        target_user_id = target_user["id"]

        resource_id = self.create("resource-to-share-user-id")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert not sharing_response["users_shared_with"]

        payload = {"user_ids": [target_user_id]}
        sharing_response = self._set_resource_sharing(resource_id, action="share_with_users", payload=payload)
        assert sharing_response["users_shared_with"]
        assert sharing_response["users_shared_with"][0]["id"] == target_user_id

        payload = {"user_ids": []}
        sharing_response = self._set_resource_sharing(resource_id, action="share_with_users", payload=payload)
        assert not sharing_response["users_shared_with"]

    def test_sharing_with_user_email(self):
        target_user = self._setup_user("target@user.com")
        target_user_email = target_user["email"]

        resource_id = self.create("resource-to-share-user-email")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert not sharing_response["users_shared_with"]

        payload = {"user_ids": [target_user_email]}
        sharing_response = self._set_resource_sharing(resource_id, action="share_with_users", payload=payload)
        assert sharing_response["users_shared_with"]
        assert sharing_response["users_shared_with"][0]["email"] == target_user_email

        payload = {"user_ids": []}
        sharing_response = self._set_resource_sharing(resource_id, action="share_with_users", payload=payload)
        assert not sharing_response["users_shared_with"]

    def test_update_sharing_with_users(self):
        target_user_list = ["target01@user.com", "target02@user.com"]
        additional_user_list = ["add01@user.com", "add02@user.com"]
        all_user_emails = target_user_list + additional_user_list
        for email in all_user_emails:
            self._setup_user(email)

        resource_id = self.create("resource-to-share-and-update")

        payload = {"user_ids": all_user_emails}
        sharing_response = self._set_resource_sharing(resource_id, action="share_with_users", payload=payload)
        assert sharing_response["users_shared_with"]
        assert len(sharing_response["users_shared_with"]) == len(all_user_emails)

        # We just keep target users so additional users should be removed
        payload = {"user_ids": target_user_list}
        sharing_response = self._set_resource_sharing(resource_id, action="share_with_users", payload=payload)
        assert len(sharing_response["users_shared_with"]) == len(target_user_list)
        assert additional_user_list not in sharing_response["users_shared_with"]

    def test_sharing_with_invalid_user(self):
        invalid_user_email = "unknown@user.com"

        resource_id = self.create("resource-to-share-user-unknown")

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert not sharing_response["users_shared_with"]

        payload = {"user_ids": [invalid_user_email]}
        sharing_response = self._set_resource_sharing(resource_id, action="share_with_users", payload=payload)
        assert not sharing_response["users_shared_with"]
        assert sharing_response["errors"]
        assert invalid_user_email in sharing_response["errors"][0]

    def test_share_recipient_access(self):
        [recipient_email] = self._setup_recipients(1)
        resource_id = self.create("resource-to-share-recipient-access")
        self._share_with(resource_id, [recipient_email])

        with self._different_user(recipient_email):
            self._assert_get_status(resource_id, 200)
            self._set_resource_sharing(
                resource_id, "share_with_users", payload={"user_ids": []}, expect_response_status=403
            )

        self._share_with(resource_id, [])
        with self._different_user(recipient_email):
            self._assert_get_status(resource_id, 403)

    def test_unshare_with_me(self):
        recipient_email, other_recipient_email = self._setup_recipients(2)
        resource_id = self.create("resource-to-unshare-with-me")
        self._share_with(resource_id, [recipient_email, other_recipient_email])

        with self._different_user(recipient_email):
            self._assert_status_code_is(self._unshare_with_me(resource_id), 204)
            self._assert_get_status(resource_id, 403)
            self._assert_unshare_with_me_not_found(resource_id)

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert [u["email"] for u in sharing_response["users_shared_with"]] == [other_recipient_email]

    def test_unshare_with_me_requires_share(self):
        [recipient_email] = self._setup_recipients(1)
        resource_id = self.create("resource-to-unshare-with-me-unshared")
        self._share_with(resource_id, [recipient_email])

        self._assert_unshare_with_me_not_found(resource_id)
        with self._different_user(f"stranger-{uuid4()}@user.com"):
            self._assert_unshare_with_me_not_found(resource_id)
        with self._different_user(anon=True):
            self._assert_status_code_is(self._unshare_with_me(resource_id), 403)

        sharing_response = self._get_resource_sharing_status(resource_id)
        assert [u["email"] for u in sharing_response["users_shared_with"]] == [recipient_email]

    def test_set_slug(self):
        resource_id = self.create("resource-to-set-slug")
        other_resource_id = self.create("other-resource-to-set-slug")

        new_slug = f"new-slug-{uuid4()}"
        response = self._set_slug(resource_id, new_slug)
        self._assert_status_code_is_ok(response)

        # Slugs must be unique for the same user/resource
        response = self._set_slug(other_resource_id, new_slug)
        self._assert_status_code_is(response, 409)

        # Other users cannot change the slug if they don't own the resource
        with self._different_user():
            response = self._set_slug(resource_id, "another-slug")
            self._assert_status_code_is(response, 403)

    def _setup_recipients(self, count: int) -> list[str]:
        emails = [f"recipient-{uuid4()}@user.com" for _ in range(count)]
        for email in emails:
            self._setup_user(email)
        return emails

    def _assert_get_status(self, resource_id: str, status: int):
        self._assert_status_code_is(self._get(f"{self.api_name}/{resource_id}"), status)

    def _get_resource_sharing_status(self, resource_id: str):
        sharing_response = self._get(f"{self.api_name}/{resource_id}/sharing")
        self._assert_status_code_is(sharing_response, 200)
        return sharing_response.json()

    def _set_resource_sharing(
        self, resource_id: str, action: str, payload: Any = None, expect_response_status: int = 200
    ):
        sharing_response = self._put(f"{self.api_name}/{resource_id}/{action}", data=payload, json=True)
        self._assert_status_code_is(sharing_response, expect_response_status)
        return sharing_response.json()

    def _share_with(self, resource_id: str, users: list[str]):
        return self._set_resource_sharing(resource_id, action="share_with_users", payload={"user_ids": users})

    def _unshare_with_me(self, resource_id: str):
        return self._put(f"{self.api_name}/{resource_id}/unshare_with_me")

    def _assert_unshare_with_me_not_found(self, resource_id: str):
        response = self._unshare_with_me(resource_id)
        self._assert_status_code_is(response, 404)
        self._assert_error_code_is(response, error_codes.error_codes_by_name["USER_OBJECT_NOT_FOUND"])

    def _set_slug(self, resource_id: str, new_slug: str):
        payload = {"new_slug": new_slug}
        response = self._put(f"{self.api_name}/{resource_id}/slug", data=payload, json=True)
        return response

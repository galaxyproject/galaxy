from typing import Any
from unittest import SkipTest

from galaxy_test.base.api import UsesApiTestCaseMixin


class SharingApiTests(UsesApiTestCaseMixin):
    """ Includes some tests for the sharing functionality of a particular resource type."""

    # The api_name has to be set to the appropiate value in the class using these tests.
    api_name: str

    def create(self, name: str) -> str:
        """Creates a shareable resource with the given name and returns it's ID.

        :param name: The name of the shareable resource to create.
        :type name: str
        :return: The ID of the resource.
        :rtype: str
        """
        raise SkipTest("Abstract")

    def test_get_sharing_info(self):
        resource_id = self.create("resource-to-share")
        sharing_response = self._get_resource_sharing_info(resource_id)
        self._assert_has_keys(sharing_response, "title", "importable", "id", "username_and_slug", "published", "users_shared_with")

    def test_sharing_make_accessible_via_link(self):
        resource_id = self.create("resource-to-make-accessible-via-link")

        sharing_response = self._get_resource_sharing_info(resource_id)
        assert sharing_response["importable"] is False

        payload = {"action": "make_accessible_via_link"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is True

    def test_sharing_make_accessible_and_publish(self):
        resource_id = self.create("resource-to-publish")

        sharing_response = self._get_resource_sharing_info(resource_id)
        assert sharing_response["importable"] is False
        assert sharing_response["published"] is False

        payload = {"action": "make_accessible_and_publish"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is True
        assert sharing_response["published"] is True

    def test_sharing_publish_not_accessible_raises_400(self):
        resource_id = self.create("resource-to-publish-not-accesible")

        sharing_response = self._get_resource_sharing_info(resource_id)
        assert sharing_response["importable"] is False

        payload = {"action": "publish"}
        sharing_response = self._set_resource_sharing(resource_id, payload, expect_response_status=400)

    def test_sharing_disable_link_access(self):
        resource_id = self.create("resource-to-disable-link-access")

        payload = {"action": "make_accessible_via_link"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is True

        payload = {"action": "disable_link_access"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is False

    def test_sharing_unpublish(self):
        resource_id = self.create("resource-to-unpublish")

        sharing_response = self._get_resource_sharing_info(resource_id)

        payload = {"action": "make_accessible_and_publish"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is True
        assert sharing_response["published"] is True

        payload = {"action": "unpublish"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is True
        assert sharing_response["published"] is False

    def test_sharing_disable_link_access_and_unpublish(self):
        resource_id = self.create("resource-to-disable-link-access-and-unpublish")

        sharing_response = self._get_resource_sharing_info(resource_id)

        payload = {"action": "make_accessible_and_publish"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is True
        assert sharing_response["published"] is True

        payload = {"action": "disable_link_access_and_unpublish"}
        sharing_response = self._set_resource_sharing(resource_id, payload)
        assert sharing_response["importable"] is False
        assert sharing_response["published"] is False

    def _get_resource_sharing_info(self, resource_id: str):
        sharing_response = self._get(f"{self.api_name}/{resource_id}/sharing")
        self._assert_status_code_is(sharing_response, 200)
        return sharing_response.json()

    def _set_resource_sharing(self, resource_id: str, payload: Any, expect_response_status: int = 200):
        sharing_response = self._post(f"{self.api_name}/{resource_id}/sharing", data=payload, json=True)
        self._assert_status_code_is(sharing_response, expect_response_status)
        return sharing_response.json()

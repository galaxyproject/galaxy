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

    def test_sharing(self):
        resource_id = self.create("resource-to-share")
        sharing_response = self._get(f"{self.api_name}/{resource_id}/sharing")
        self._assert_status_code_is(sharing_response, 200)
        self._assert_has_keys(sharing_response.json(), "title", "importable", "id", "username_and_slug", "published", "users_shared_with")

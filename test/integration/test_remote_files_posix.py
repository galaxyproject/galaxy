# Before running this test, start nginx+webdav in Docker using following command:
# docker run -v `pwd`/test/integration/webdav/data:/media  -e WEBDAV_USERNAME=alice -e WEBDAV_PASSWORD=secret1234 -p 7083:7083 jmchilton/webdavdev
# Apache Docker host (shown next) doesn't work because displayname not set in response.
# docker run -v `pwd`/test/integration/webdav:/var/lib/dav  -e AUTH_TYPE=Basic -e USERNAME=alice -e PASSWORD=secret1234  -e LOCATION=/ -p 7083:80 bytemark/webdav

from galaxy_test.base import api_asserts
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.integration_setup import (
    GROUP_A,
    GROUP_B,
    PosixFileSourceSetup,
    REQUIRED_GROUP_EXPRESSION,
    REQUIRED_ROLE_EXPRESSION,
)


class PosixFileSourceIntegrationTestCase(PosixFileSourceSetup, integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        PosixFileSourceSetup.handle_galaxy_config_kwds(
            config,
            cls,
            required_role_expression=REQUIRED_ROLE_EXPRESSION,
            required_group_expression=REQUIRED_GROUP_EXPRESSION,
        )

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_plugin_config(self):
        # Default user has required role but not required group, so cannot see plugin
        plugin_config_response = self.galaxy_interactor.get("remote_files/plugins")
        api_asserts.assert_status_code_is_ok(plugin_config_response)
        plugins = plugin_config_response.json()
        assert len(plugins) == 0
        # Admins can see plugins
        plugin_config_response = self.galaxy_interactor.get("remote_files/plugins", admin=True)
        api_asserts.assert_status_code_is_ok(plugin_config_response)
        plugins = plugin_config_response.json()
        assert len(plugins) == 1
        assert plugins[0]["type"] == "posix"
        assert plugins[0]["uri_root"] == "gxfiles://posix_test"
        assert plugins[0]["writable"] is True
        assert plugins[0]["requires_roles"] == REQUIRED_ROLE_EXPRESSION
        assert plugins[0]["requires_groups"] == REQUIRED_GROUP_EXPRESSION

    def test_allow_admin_access(self):
        data = {"target": "gxfiles://posix_test"}
        list_response = self.galaxy_interactor.get("remote_files", data, admin=True)
        self._assert_list_response_matches_fixtures(list_response)

    def test_user_access(self):
        data = {"target": "gxfiles://posix_test"}
        group_a_id = self._create_group(GROUP_A)
        group_b_id = self._create_group(GROUP_B)

        # User has role but not group
        list_response = self.galaxy_interactor.get("remote_files", data)
        self._assert_access_forbidden_response(list_response)

        # User has role and group A
        user_id = self.dataset_populator.user_id()
        self._add_user_to_group(group_a_id, user_id)
        list_response = self.galaxy_interactor.get("remote_files", data)
        self._assert_list_response_matches_fixtures(list_response)

        # Remove User from group A and add to group B
        self._remove_user_from_group(group_a_id, user_id)
        self._add_user_to_group(group_b_id, user_id)
        list_response = self.galaxy_interactor.get("remote_files", data)
        self._assert_list_response_matches_fixtures(list_response)

    def _create_group(self, group_name: str):
        payload = {
            "name": group_name,
            "user_ids": [],
        }
        response = self._post("groups", payload, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        group = response.json()[0]  # POST /api/groups returns a list
        return group["id"]

    def _add_user_to_group(self, group_id, user_id):
        update_response = self._put(f"groups/{group_id}/users/{user_id}", admin=True)
        self._assert_status_code_is_ok(update_response)

    def _remove_user_from_group(self, group_id, user_id):
        update_response = self._delete(f"groups/{group_id}/users/{user_id}", admin=True)
        self._assert_status_code_is_ok(update_response)

    def _assert_list_response_matches_fixtures(self, list_response):
        api_asserts.assert_status_code_is_ok(list_response)
        remote_files = list_response.json()
        assert len(remote_files) == 2
        if remote_files[0]["class"] == "Directory":
            dir = remote_files[0]
            file = remote_files[1]
        else:
            dir = remote_files[1]
            file = remote_files[0]
        assert file["name"] == "a"
        assert dir["name"] == "subdir1"

    def _assert_access_forbidden_response(self, response):
        api_asserts.assert_status_code_is(response, 403)

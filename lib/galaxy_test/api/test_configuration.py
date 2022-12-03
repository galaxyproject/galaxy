from galaxy_test.base.api_asserts import (
    assert_has_keys,
    assert_not_has_keys,
)
from galaxy_test.base.api_util import TEST_USER
from galaxy_test.base.decorators import requires_admin
from ._framework import ApiTestCase

TEST_KEYS_FOR_ALL_USERS = [
    "enable_unique_workflow_defaults",
    "ftp_upload_site",
    "wiki_url",
    "support_url",
    "logo_url",
    "terms_url",
    "allow_user_dataset_purge",
]
TEST_KEYS_FOR_ADMIN_ONLY = [
    "library_import_dir",
    "user_library_import_dir",
    "allow_library_path_paste",
    "allow_user_deletion",
]


class TestConfigurationApi(ApiTestCase):
    def test_whoami(self):
        response = self._get("whoami")
        self._assert_status_code_is(response, 200)
        assert response.json()["email"] == TEST_USER

    def test_normal_user_configuration(self):
        config = self._get_configuration()
        assert_has_keys(config, *TEST_KEYS_FOR_ALL_USERS)
        assert_not_has_keys(config, *TEST_KEYS_FOR_ADMIN_ONLY)

    @requires_admin
    def test_admin_user_configuration(self):
        config = self._get_configuration(admin=True)
        assert_has_keys(config, *TEST_KEYS_FOR_ALL_USERS)
        assert_has_keys(config, *TEST_KEYS_FOR_ADMIN_ONLY)

    def test_normal_user_decode_id(self):
        decode_response = self._get("configuration/decode/badhombre", admin=False)
        self._assert_status_code_is(decode_response, 403)

    def _get_configuration(self, data=None, admin=False):
        data = data or {}
        response = self._get("configuration", data=data, admin=admin)
        self._assert_status_code_is(response, 200)
        configuration = response.json()
        return configuration

    def test_version(self):
        response = self._get("version")
        self._assert_status_code_is(response, 200)
        data = response.json()
        assert "version_major" in data
        assert "version_minor" in data

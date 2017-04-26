from base import api
from base.api_asserts import (
    assert_has_keys,
    assert_not_has_keys,
)

TEST_KEYS_FOR_ALL_USERS = [
    'enable_unique_workflow_defaults',
    'ftp_upload_site',
    'ftp_upload_dir',
    'wiki_url',
    'support_url',
    'logo_url',
    'terms_url',
    'allow_user_dataset_purge',
]
TEST_KEYS_FOR_ADMIN_ONLY = [
    'library_import_dir',
    'user_library_import_dir',
    'allow_library_path_paste',
    'allow_user_deletion',
]


class ConfigurationApiTestCase(api.ApiTestCase):

    def test_normal_user_configuration(self):
        config = self._get_configuration()
        assert_has_keys(config, *TEST_KEYS_FOR_ALL_USERS)
        assert_not_has_keys(config, *TEST_KEYS_FOR_ADMIN_ONLY)

    def test_admin_user_configuration(self):
        config = self._get_configuration(admin=True)
        assert_has_keys(config, *TEST_KEYS_FOR_ALL_USERS)
        assert_has_keys(config, *TEST_KEYS_FOR_ADMIN_ONLY)

    def _get_configuration(self, data={}, admin=False):
        response = self._get("configuration", data=data, admin=admin)
        self._assert_status_code_is(response, 200)
        configuration = response.json()
        return configuration

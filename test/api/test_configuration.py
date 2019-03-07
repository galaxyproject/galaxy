from base import api
from base.api_asserts import (
    assert_has_keys,
    assert_not_has_keys,
)
from base.populators import (
    LibraryPopulator
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

    def setUp(self):
        super(ConfigurationApiTestCase, self).setUp()
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

    def test_normal_user_configuration(self):
        config = self._get_configuration()
        assert_has_keys(config, *TEST_KEYS_FOR_ALL_USERS)
        assert_not_has_keys(config, *TEST_KEYS_FOR_ADMIN_ONLY)

    def test_admin_user_configuration(self):
        config = self._get_configuration(admin=True)
        assert_has_keys(config, *TEST_KEYS_FOR_ALL_USERS)
        assert_has_keys(config, *TEST_KEYS_FOR_ADMIN_ONLY)

    def test_admin_decode_id(self):
        new_lib = self.library_populator.new_library('DecodeTestLibrary')
        decode_response = self._get("configuration/decode/" + new_lib["id"], admin=True)
        response_id = decode_response.json()["decoded_id"]
        decoded_library_id = self.security.decode_id(new_lib["id"])
        assert decoded_library_id == response_id
        # fake valid folder id by prepending F
        valid_encoded_folder_id = 'F' + new_lib["id"]
        folder_decode_response = self._get("configuration/decode/" + valid_encoded_folder_id, admin=True)
        folder_response_id = folder_decode_response.json()["decoded_id"]
        assert decoded_library_id == folder_response_id

    def test_normal_user_decode_id(self):
        decode_response = self._get("configuration/decode/badhombre", admin=False)
        self._assert_status_code_is(decode_response, 403)

    def _get_configuration(self, data={}, admin=False):
        response = self._get("configuration", data=data, admin=admin)
        self._assert_status_code_is(response, 200)
        configuration = response.json()
        return configuration

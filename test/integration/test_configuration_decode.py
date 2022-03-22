from galaxy_test.base.populators import LibraryPopulator
from galaxy_test.driver import integration_util


class ConfigurationDecodeIntegrationTestCase(integration_util.IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

    def test_admin_decode_id(self):
        new_lib = self.library_populator.new_library("DecodeTestLibrary")
        decode_response = self._get("configuration/decode/" + new_lib["id"], admin=True)
        response_id = decode_response.json()["decoded_id"]
        decoded_library_id = self._app.security.decode_id(new_lib["id"])
        assert decoded_library_id == response_id
        # fake valid folder id by prepending F
        valid_encoded_folder_id = "F" + new_lib["id"]
        folder_decode_response = self._get("configuration/decode/" + valid_encoded_folder_id, admin=True)
        folder_response_id = folder_decode_response.json()["decoded_id"]
        assert decoded_library_id == folder_response_id

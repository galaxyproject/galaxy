import json
import os
from typing import Any, cast

from requests import (
    get,
    put
)

from ._framework import ApiTestCase

TEST_USER_EMAIL = "vault_test_user@bx.psu.edu"


class VaultApiTestCase(ApiTestCase):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["vault_config_file"] = os.path.join(os.path.dirname(__file__), "vault_conf.yml")
        config["user_preferences_extra_conf_path"] = os.path.join(os.path.dirname(__file__), "user_preferences_extra_conf.yml")

    def test_extra_prefs_vault_storage(self):
        user = self._setup_user(TEST_USER_EMAIL)
        url = self.__url("information/inputs", user)
        app = cast(Any, self._test_driver.app if self._test_driver else None)

        # create some initial data
        put(url, data=json.dumps({
            "vaulttestsection|client_id": "hello_client_id",
            "vaulttestsection|client_secret": "hello_client_secret",
        }))

        # retrieve saved data
        response = get(url).json()

        def get_input_by_name(inputs, name):
            return [input for input in inputs if input['name'] == name][0]

        inputs = [section for section in response["inputs"] if section['name'] == 'vaulttestsection'][0]["inputs"]
        db_user = app.model.context.query(app.model.User).filter(app.model.User.email == user['email']).first()

        # value should be what we saved
        input_client_id = get_input_by_name(inputs, 'client_id')
        self.assertEqual(input_client_id['value'], "hello_client_id")

        # however, this value should not be in the vault
        self.assertIsNone(app.vault.read_secret(f"user/{db_user.id}/preferences/vaulttestsection/client_id"))
        # it should be in the user preferences model
        self.assertEqual(db_user.extra_preferences['vaulttestsection|client_id'], "hello_client_id")

        # the secret however, was configured to be stored in the vault
        input_client_secret = get_input_by_name(inputs, 'client_secret')
        self.assertEqual(input_client_secret['value'], "hello_client_secret")
        self.assertEqual(app.vault.read_secret(
            f"user/{db_user.id}/preferences/vaulttestsection/client_secret"), "hello_client_secret")
        # it should not be stored in the user preferences model
        self.assertIsNone(db_user.extra_preferences['vaulttestsection|client_secret'])

    def __url(self, action, user):
        return self._api_url(f"users/{user['id']}/{action}", params=dict(key=self.master_api_key))

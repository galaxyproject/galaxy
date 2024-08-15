import json
import os
from typing import (
    Any,
    cast,
)

from requests import (
    get,
    put,
)

from galaxy.model.db.user import get_user_by_email
from galaxy_test.driver import integration_util

TEST_USER_EMAIL = "vault_test_user@bx.psu.edu"


class TestExtraUserPreferences(integration_util.IntegrationTestCase, integration_util.ConfiguresDatabaseVault):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)
        config["user_preferences_extra_conf_path"] = os.path.join(
            os.path.dirname(__file__), "user_preferences_extra_conf.yml"
        )

    def test_extra_prefs_vault_storage(self):
        user = self._setup_user(TEST_USER_EMAIL)
        url = self.__url("information/inputs", user)
        app = cast(Any, self._test_driver.app if self._test_driver else None)
        db_user = self._get_dbuser(app, user)

        # create some initial data
        put(
            url,
            data=json.dumps(
                {
                    "vaulttestsection|client_id": "hello_client_id",
                    "vaulttestsection|client_secret": "hello_client_secret",
                    "vaulttestsection|refresh_token": "a_super_secret_value",
                }
            ),
        )

        # retrieve saved data
        response = get(url).json()

        def get_input_by_name(inputs, name):
            return [input for input in inputs if input["name"] == name][0]

        inputs = [section for section in response["inputs"] if section["name"] == "vaulttestsection"][0]["inputs"]

        # value should be what we saved
        input_client_id = get_input_by_name(inputs, "client_id")
        assert input_client_id["value"] == "hello_client_id"

        # however, this value should not be in the vault
        assert app.vault.read_secret(f"user/{db_user.id}/preferences/vaulttestsection/client_id") is None
        # it should be in the user preferences model
        assert db_user.extra_preferences["vaulttestsection|client_id"] == "hello_client_id"

        # the secret however, was configured to be stored in the vault
        input_client_secret = get_input_by_name(inputs, "client_secret")
        assert input_client_secret["value"] == "hello_client_secret"
        assert (
            app.vault.read_secret(f"user/{db_user.id}/preferences/vaulttestsection/client_secret")
            == "hello_client_secret"
        )
        # it should not be stored in the user preferences model
        assert db_user.extra_preferences["vaulttestsection|client_secret"] is None

        # secret type values should not be retrievable by the client
        input_refresh_token = get_input_by_name(inputs, "refresh_token")
        assert input_refresh_token["value"] != "a_super_secret_value"
        assert input_refresh_token["value"] == "__SECRET_PLACEHOLDER__"

        # however, that secret value should be correctly stored on the server
        assert (
            app.vault.read_secret(f"user/{db_user.id}/preferences/vaulttestsection/refresh_token")
            == "a_super_secret_value"
        )

    def test_extra_prefs_vault_storage_update_secret(self):
        user = self._setup_user(TEST_USER_EMAIL)
        url = self.__url("information/inputs", user)
        app = cast(Any, self._test_driver.app if self._test_driver else None)
        db_user = self._get_dbuser(app, user)

        # write the initial secret value
        put(
            url,
            data=json.dumps(
                {
                    "vaulttestsection|refresh_token": "a_new_secret_value",
                }
            ),
        )

        # attempt to overwrite it with placeholder
        put(
            url,
            data=json.dumps(
                {
                    "vaulttestsection|refresh_token": "__SECRET_PLACEHOLDER__",
                }
            ),
        )

        # value should not have been overwritten
        assert (
            app.vault.read_secret(f"user/{db_user.id}/preferences/vaulttestsection/refresh_token")
            == "a_new_secret_value"
        )

        # write a new value
        put(
            url,
            data=json.dumps(
                {
                    "vaulttestsection|refresh_token": "an_updated_secret_value",
                }
            ),
        )

        # value should now be overwritten
        assert (
            app.vault.read_secret(f"user/{db_user.id}/preferences/vaulttestsection/refresh_token")
            == "an_updated_secret_value"
        )

    def __url(self, action, user):
        return self._api_url(f"users/{user['id']}/{action}", params=dict(key=self.master_api_key))

    def _get_dbuser(self, app, user):
        return get_user_by_email(app.model.session, user["email"])

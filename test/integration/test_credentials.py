from galaxy_test.driver import integration_util


class TestCredentialsApi(integration_util.IntegrationTestCase, integration_util.ConfiguresDatabaseVault):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)

    def test_provide_credential(self):
        created_user_credentials = self._populate_user_credentials()
        assert created_user_credentials[0]["current_group_name"] == "default"

    def test_list_user_credentials(self):
        list_user_credentials = self._list_user_credentials()
        assert len(list_user_credentials) > 0

    def test_delete_service_credentials(self):
        list_user_credentials = self._list_user_credentials()
        user_credentials_id = list_user_credentials[0]["id"]
        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}")
        self._assert_status_code_is(response, 204)

    def test_delete_credentials(self):
        created_user_credentials = self._populate_user_credentials()
        user_credentials_id = created_user_credentials[0]["id"]
        group_id = list(created_user_credentials[0]["groups"].values())[0]["id"]
        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}/{group_id}")
        self._assert_status_code_is(response, 204)

    def test_invalid_provide_credential(self):
        payload = {
            "source_type": "tool",
            "source_id": "test_tool",
            "credentials": [
                {
                    "reference": "invalid_test_service",
                    "current_group": "invalid_group_name",
                    "groups": [{"name": "default", "variables": [], "secrets": []}],
                }
            ],
        }
        response = self._post(f"/api/users/current/credentials", data=payload, json=True)
        self._assert_status_code_is(response, 400)

    def test_delete_not_existing_service_credentials(self):
        response = self._delete("/api/users/current/credentials/f2db41e1fa331b3e")
        self._assert_status_code_is(response, 400)

    def test_delete_not_existing_credentials(self):
        response = self._delete("/api/users/current/credentials/f2db41e1fa331b3e/f2db41e1fa331b3e")
        self._assert_status_code_is(response, 400)

    def _populate_user_credentials(self):
        payload = {
            "source_type": "tool",
            "source_id": "test_tool",
            "credentials": [
                {
                    "reference": "test_service",
                    "current_group": "default",
                    "groups": [
                        {
                            "name": "default",
                            "variables": [{"name": "username", "value": "user"}],
                            "secrets": [{"name": "password", "value": "pass"}],
                        }
                    ],
                }
            ],
        }
        response = self._post(f"/api/users/current/credentials", data=payload, json=True)
        self._assert_status_code_is(response, 200)
        return response.json()

    def _list_user_credentials(self):
        response = self._get(f"/api/users/current/credentials")
        self._assert_status_code_is(response, 200)
        return response.json()

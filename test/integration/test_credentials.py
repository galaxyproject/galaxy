from uuid import uuid4

from galaxy_test.driver import integration_util


class TestCredentialsApi(integration_util.IntegrationTestCase, integration_util.ConfiguresDatabaseVault):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)

    def test_provide_credential(self):
        created_user_credentials = self._provide_user_credentials()
        assert len(created_user_credentials) == 1
        assert created_user_credentials[0]["current_group_name"] == "default"
        assert len(created_user_credentials[0]["groups"]["default"]["variables"]) == 1
        assert len(created_user_credentials[0]["groups"]["default"]["secrets"]) == 3

    def test_anon_users_cannot_provide_credentials(self):
        payload = self._build_credentials_payload()
        response = self._post("/api/users/current/credentials", data=payload, json=True, anon=True)
        self._assert_status_code_is(response, 403)

    def test_list_user_credentials(self):
        source_id = f"test_tool_list_credentials_{uuid4()}"
        payload = self._build_credentials_payload(source_id=source_id)
        self._provide_user_credentials(payload)

        # Check there is at least one credential
        response = self._get("/api/users/current/credentials")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) > 0

        # Check the specific credential exists
        response = self._get(f"/api/users/current/credentials?source_type=tool&source_id={source_id}")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) == 1
        assert list_user_credentials[0]["source_id"] == source_id

    def test_other_users_cannot_list_credentials(self):
        source_id = f"test_others_cant_list_credentials_{uuid4()}"
        payload = self._build_credentials_payload(source_id=source_id)
        self._provide_user_credentials(payload)

        response = self._get(f"/api/users/current/credentials?source_type=tool&source_id={source_id}")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) == 1
        assert list_user_credentials[0]["source_id"] == source_id

        with self._different_user():
            response = self._get(f"/api/users/current/credentials?source_type=tool&source_id={source_id}")
            self._assert_status_code_is(response, 200)
            list_user_credentials = response.json()
            assert len(list_user_credentials) == 0

    def test_list_by_source_id_requires_source_type(self):
        response = self._get("/api/users/current/credentials?source_id=test_tool")
        self._assert_status_code_is(response, 400)

    def test_list_unsupported_source_type(self):
        response = self._get("/api/users/current/credentials?source_type=invalid")
        self._assert_status_code_is(response, 400)

    def test_add_group_to_credentials(self):
        source_id = f"test_tool_add_group_{uuid4()}"
        payload = self._build_credentials_payload(source_id=source_id)
        user_credentials = self._provide_user_credentials(payload)
        assert len(user_credentials) == 1
        assert len(user_credentials[0]["groups"]) == 1

        # Add a new group
        new_group_name = "new_group"
        payload = self._add_group_and_set_as_current(payload, new_group_name)
        updated_user_credentials = self._provide_user_credentials(payload)
        assert len(updated_user_credentials) == 1
        assert updated_user_credentials[0]["current_group_name"] == new_group_name
        assert len(updated_user_credentials[0]["groups"]) == 2

    def test_delete_service_credentials(self):
        # Create credentials
        source_id = f"test_tool_delete_service_credentials_{uuid4()}"
        payload = self._build_credentials_payload(source_id=source_id)
        created_user_credentials = self._provide_user_credentials(payload)
        user_credentials_id = created_user_credentials[0]["id"]

        # Check credentials exist
        response = self._get(f"/api/users/current/credentials?source_type=tool&source_id={source_id}")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) == 1
        assert list_user_credentials[0]["source_id"] == source_id

        # Delete credentials
        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}")
        self._assert_status_code_is(response, 204)

        # Check credentials are deleted
        response = self._get(f"/api/users/current/credentials?source_type=tool&source_id={source_id}")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) == 0

    def test_delete_credentials_group(self):
        target_group_name = "new_group"
        source_id = f"test_tool_delete_credentials_group_{uuid4()}"
        payload = self._build_credentials_payload(source_id=source_id)
        payload = self._add_group_and_set_as_current(payload, target_group_name)
        user_credentials = self._provide_user_credentials(payload)

        # Check credentials exist with the new group
        response = self._get(f"/api/users/current/credentials?source_type=tool&source_id={source_id}")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) == 1
        assert list_user_credentials[0]["source_id"] == source_id
        assert list_user_credentials[0]["current_group_name"] == target_group_name

        # Delete the group
        user_credentials_id = user_credentials[0]["id"]
        target_group = user_credentials[0]["groups"][target_group_name]
        group_id = target_group["id"]
        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}/{group_id}")
        self._assert_status_code_is(response, 204)

        # Check group is deleted
        response = self._get(f"/api/users/current/credentials?source_type=tool&source_id={source_id}")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) == 1
        assert len(list_user_credentials[0]["groups"]) == 1
        assert list_user_credentials[0]["current_group_name"] == "default"

    def test_provide_credential_invalid_group(self):
        payload = {
            "source_type": "tool",
            "source_id": "test_tool",
            "credentials": [
                {
                    "service_reference": "invalid_test_service",
                    "current_group": "invalid_group_name",
                    "groups": [{"name": "default", "variables": [], "secrets": []}],
                }
            ],
        }
        response = self._post("/api/users/current/credentials", data=payload, json=True)
        self._assert_status_code_is(response, 400)

    def test_delete_nonexistent_service_credentials(self):
        response = self._delete("/api/users/current/credentials/f2db41e1fa331b3e")
        self._assert_status_code_is(response, 400)

    def test_delete_nonexistent_credentials_group(self):
        response = self._delete("/api/users/current/credentials/f2db41e1fa331b3e/f2db41e1fa331b3e")
        self._assert_status_code_is(response, 400)

    def test_cannot_delete_default_credential_group(self):
        created_user_credentials = self._provide_user_credentials()
        user_credentials_id = created_user_credentials[0]["id"]
        default_group = created_user_credentials[0]["groups"]["default"]
        group_id = default_group["id"]
        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}/{group_id}")
        self._assert_status_code_is(response, 400)

    def _provide_user_credentials(self, payload=None):
        payload = payload or self._build_credentials_payload()
        response = self._post("/api/users/current/credentials", data=payload, json=True)
        self._assert_status_code_is(response, 200)
        return response.json()

    def _build_credentials_payload(self, source_type: str = "tool", source_id: str = "test_tool"):
        return {
            "source_type": source_type,
            "source_id": source_id,
            "credentials": [
                {
                    "service_reference": "test_service",
                    "current_group": "default",
                    "groups": [
                        {
                            "name": "default",
                            "variables": [{"name": "server", "value": "http://localhost:8080"}],
                            "secrets": [
                                {"name": "username", "value": "user"},
                                {"name": "password", "value": "pass"},
                                {"name": "token", "value": "key"},
                            ],
                        }
                    ],
                },
            ],
        }

    def _add_group_and_set_as_current(self, payload: dict, new_group_name: str):
        service_credentials = payload["credentials"][0]
        service_credentials["current_group"] = new_group_name
        service_credentials_groups = service_credentials["groups"]
        assert isinstance(service_credentials_groups, list)
        service_credentials_groups.append(
            {
                "name": new_group_name,
                "variables": [{"name": "server", "value": "http://localhost:8080"}],
                "secrets": [
                    {"name": "username", "value": "user"},
                    {"name": "password", "value": "pass"},
                    {"name": "token", "value": "key"},
                ],
            }
        )
        assert len(payload["credentials"][0]["groups"]) == 2
        return payload

from galaxy_test.base.populators import skip_without_tool
from galaxy_test.driver import integration_util

CREDENTIALS_TEST_TOOL = "secret_tool"


class TestCredentialsApi(integration_util.IntegrationTestCase, integration_util.ConfiguresDatabaseVault):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_provide_credential(self):
        created_user_credentials = self._provide_user_credentials()
        assert len(created_user_credentials) == 1
        assert created_user_credentials[0]["current_group_name"] == "default"
        assert len(created_user_credentials[0]["groups"]["default"]["variables"]) == 1
        assert len(created_user_credentials[0]["groups"]["default"]["secrets"]) == 2

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_anon_users_cannot_provide_credentials(self):
        payload = self._build_credentials_payload()
        response = self._post("/api/users/current/credentials", data=payload, json=True, anon=True)
        self._assert_status_code_is(response, 403)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_list_user_credentials(self):
        self._provide_user_credentials()

        # Check there is at least one credential
        response = self._get("/api/users/current/credentials")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) > 0

        # Check the specific credential exists
        self._check_credentials_exist()

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_other_users_cannot_list_credentials(self):
        self._provide_user_credentials()

        self._check_credentials_exist()

        with self._different_user():
            self._check_credentials_exist(num_credentials=0)

    def test_list_by_source_id_requires_source_type(self):
        response = self._get("/api/users/current/credentials?source_id={CREDENTIALS_TEST_TOOL}")
        self._assert_status_code_is(response, 400)

    def test_list_unsupported_source_type(self):
        response = self._get("/api/users/current/credentials?source_type=invalid")
        self._assert_status_code_is(response, 400)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_add_group_to_credentials(self):
        payload = self._build_credentials_payload()
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

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_delete_service_credentials(self):
        # Create credentials
        created_user_credentials = self._provide_user_credentials()
        user_credentials_id = created_user_credentials[0]["id"]

        # Check credentials exist
        self._check_credentials_exist()

        # Delete credentials
        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}")
        self._assert_status_code_is(response, 204)

        # Check credentials are deleted
        self._check_credentials_exist(num_credentials=0)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_delete_credentials_group(self):
        target_group_name = "new_group"
        payload = self._build_credentials_payload()
        payload = self._add_group_and_set_as_current(payload, target_group_name)
        user_credentials = self._provide_user_credentials(payload)

        # Check credentials exist with the new group
        list_user_credentials = self._check_credentials_exist()
        assert list_user_credentials[0]["current_group_name"] == target_group_name

        # Delete the group
        user_credentials_id = user_credentials[0]["id"]
        target_group = user_credentials[0]["groups"][target_group_name]
        group_id = target_group["id"]
        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}/{group_id}")
        self._assert_status_code_is(response, 204)

        # Check group is deleted
        list_user_credentials = self._check_credentials_exist()
        assert len(list_user_credentials[0]["groups"]) == 1
        assert list_user_credentials[0]["current_group_name"] == "default"

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_provide_credential_invalid_group(self):
        payload = {
            "source_type": "tool",
            "source_id": CREDENTIALS_TEST_TOOL,
            "source_version": "test",
            "credentials": [
                {
                    "name": "service1",
                    "version": "1",
                    "current_group": "invalid_group_name",
                    "groups": [{"name": "default", "variables": [], "secrets": []}],
                }
            ],
        }
        response = self._post("/api/users/current/credentials", data=payload, json=True)
        self._assert_status_code_is(response, 400)

    def test_invalid_source_type(self):
        payload = self._build_credentials_payload(source_type="invalid_source_type")
        self._provide_user_credentials(payload, status_code=400)

    def test_not_existing_tool(self):
        payload = self._build_credentials_payload(source_id="nonexistent_tool")
        self._provide_user_credentials(payload, status_code=404)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_not_existing_tool_version(self):
        payload = self._build_credentials_payload(source_version="nonexistent_tool_version")
        self._provide_user_credentials(payload, status_code=404)

    def test_not_existing_service_name(self):
        payload = self._build_credentials_payload(service_name="nonexistent_service")
        self._provide_user_credentials(payload, status_code=404)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_not_existing_service_version(self):
        payload = self._build_credentials_payload(service_version="nonexistent_service_version")
        self._provide_user_credentials(payload, status_code=404)

    def test_delete_nonexistent_service_credentials(self):
        response = self._delete("/api/users/current/credentials/f2db41e1fa331b3e")
        self._assert_status_code_is(response, 400)

    def test_delete_nonexistent_credentials_group(self):
        response = self._delete("/api/users/current/credentials/f2db41e1fa331b3e/f2db41e1fa331b3e")
        self._assert_status_code_is(response, 400)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_cannot_delete_default_credential_group(self):
        created_user_credentials = self._provide_user_credentials()
        user_credentials_id = created_user_credentials[0]["id"]
        default_group = created_user_credentials[0]["groups"]["default"]
        group_id = default_group["id"]
        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}/{group_id}")
        self._assert_status_code_is(response, 400)

    def _provide_user_credentials(self, payload=None, status_code=200):
        payload = payload or self._build_credentials_payload()
        response = self._post("/api/users/current/credentials", data=payload, json=True)
        self._assert_status_code_is(response, status_code)
        if status_code == 200:
            return response.json()
        return []

    def _build_credentials_payload(
        self,
        source_type: str = "tool",
        source_id: str = CREDENTIALS_TEST_TOOL,
        source_version: str = "test",
        service_name: str = "service1",
        service_version: str = "1",
    ):
        return {
            "source_type": source_type,
            "source_id": source_id,
            "source_version": source_version,
            "credentials": [
                {
                    "name": service_name,
                    "version": service_version,
                    "current_group": "default",
                    "groups": [
                        {
                            "name": "default",
                            "variables": [{"name": "server", "value": "http://localhost:8080"}],
                            "secrets": [
                                {"name": "username", "value": "user"},
                                {"name": "password", "value": "pass"},
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
                ],
            }
        )
        assert len(payload["credentials"][0]["groups"]) == 2
        return payload

    def _check_credentials_exist(self, source_id: str = CREDENTIALS_TEST_TOOL, num_credentials: int = 1):
        response = self._get(f"/api/users/current/credentials?source_type=tool&source_id={source_id}")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) == num_credentials
        if num_credentials > 0:
            assert list_user_credentials[0]["source_id"] == source_id

        return list_user_credentials

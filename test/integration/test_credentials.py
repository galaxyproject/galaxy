from galaxy_test.base.api_util import random_name
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
        payload = self._build_credentials_payload(group_name="default")
        created_credential_group = self._provide_user_credentials(payload=payload)
        assert created_credential_group["name"] == "default"
        assert len(created_credential_group["variables"]) == 1
        assert len(created_credential_group["secrets"]) == 2

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
        # Use unique group names to avoid interference from other tests
        initial_group = random_name()

        # First, create initial credentials with a unique group
        payload = self._build_credentials_payload(group_name=initial_group)
        self._provide_user_credentials(payload)
        initial_credentials = self._check_credentials_exist()
        assert len(initial_credentials) == 1

        # Should have only our group (plus any leftover groups from other tests)
        groups_before = {group["name"]: group for group in initial_credentials[0]["groups"]}
        assert initial_group in groups_before

        # Create a new group with the same service credentials
        second_group = random_name()
        new_payload = self._build_credentials_payload(group_name=second_group)
        self._provide_user_credentials(new_payload)

        # Check that both our groups exist
        updated_credentials = self._check_credentials_exist()
        assert len(updated_credentials) == 1

        # Find our specific groups by name
        groups_after = {group["name"]: group for group in updated_credentials[0]["groups"]}
        assert initial_group in groups_after
        assert second_group in groups_after

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_delete_service_credentials(self):
        # Create credentials
        self._provide_user_credentials()

        # Check credentials exist and get the service credentials ID
        credentials_list = self._check_credentials_exist()
        service_credentials_id = credentials_list[0]["id"]

        # Delete the entire service credentials
        response = self._delete(f"/api/users/current/credentials/{service_credentials_id}")
        self._assert_status_code_is(response, 204)

        # Check credentials are deleted
        self._check_credentials_exist(num_credentials=0)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_delete_credentials_group(self):
        # Use unique group names to avoid test interference
        initial_group = random_name()
        target_group_name = random_name()

        # Create initial credentials with unique group
        payload1 = self._build_credentials_payload(group_name=initial_group)
        self._provide_user_credentials(payload1)

        # Add a new group
        new_payload = self._build_credentials_payload(group_name=target_group_name)
        self._provide_user_credentials(new_payload)

        # Check credentials exist with both our groups
        list_user_credentials = self._check_credentials_exist()
        assert len(list_user_credentials) == 1

        groups_before = {group["name"]: group for group in list_user_credentials[0]["groups"]}
        assert initial_group in groups_before
        assert target_group_name in groups_before

        # Get the user credentials ID and find target group ID
        user_credentials_id = list_user_credentials[0]["id"]
        target_group_id = groups_before[target_group_name]["id"]

        # Set the new group as current
        select_payload = {
            "source_type": "tool",
            "source_id": CREDENTIALS_TEST_TOOL,
            "source_version": "test",
            "service_credentials": [{"user_credentials_id": user_credentials_id, "current_group_id": target_group_id}],
        }
        response = self._put("/api/users/current/credentials", data=select_payload, json=True)
        self._assert_status_code_is(response, 204)

        # Verify it's set as current
        list_user_credentials = self._check_credentials_exist()
        assert list_user_credentials[0]["current_group_id"] == target_group_id

        # Delete the group
        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}/{target_group_id}")
        self._assert_status_code_is(response, 204)

        # Check group is deleted - should only have our initial group left
        list_user_credentials = self._check_credentials_exist()
        groups_after = {group["name"]: group for group in list_user_credentials[0]["groups"]}
        assert target_group_name not in groups_after  # Target group should be deleted
        assert initial_group in groups_after  # Initial group should remain
        assert list_user_credentials[0]["current_group_id"] is None

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_provide_credential_invalid_group(self):
        payload = self._build_credentials_payload(group_name="")
        self._provide_user_credentials(payload, status_code=400)

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

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_invalid_credential_name(self):
        for key in ["variables", "secrets"]:
            payload = self._build_credentials_payload()
            payload["service_credential"]["group"][key][0]["name"] = "invalid_name"
            self._provide_user_credentials(payload, status_code=400)

    def test_delete_nonexistent_service_credentials(self):
        response = self._delete("/api/users/current/credentials/f2db41e1fa331b3e")
        self._assert_status_code_is(response, 400)

    def test_delete_nonexistent_credentials_group(self):
        response = self._delete("/api/users/current/credentials/f2db41e1fa331b3e/f2db41e1fa331b3e")
        self._assert_status_code_is(response, 400)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_delete_default_credential_group(self):
        created_user_credentials = self._provide_user_credentials()
        # The new API returns a single CredentialGroupResponse, not a list
        group_id = created_user_credentials["id"]

        # Get the user credentials to find the service credentials ID
        user_credentials_list = self._check_credentials_exist()
        user_credentials_id = user_credentials_list[0]["id"]

        response = self._delete(f"/api/users/current/credentials/{user_credentials_id}/{group_id}")
        self._assert_status_code_is(response, 204)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_unset_current_group(self):
        # First create credentials with a unique group
        group_name = random_name()
        payload = self._build_credentials_payload(group_name=group_name)
        self._provide_user_credentials(payload)

        # Set this group as current
        user_credentials_list = self._check_credentials_exist()
        user_credentials_id = user_credentials_list[0]["id"]
        default_group_id = None
        for group in user_credentials_list[0]["groups"]:
            if group["name"] == group_name:
                default_group_id = group["id"]
                break

        select_payload = {
            "source_type": "tool",
            "source_id": CREDENTIALS_TEST_TOOL,
            "source_version": "test",
            "service_credentials": [{"user_credentials_id": user_credentials_id, "current_group_id": default_group_id}],
        }
        response = self._put("/api/users/current/credentials", data=select_payload, json=True)
        self._assert_status_code_is(response, 204)

        # Verify it's set as current
        list_user_credentials = self._check_credentials_exist()
        current_group_id = list_user_credentials[0]["current_group_id"]
        current_group_name = None
        for group in list_user_credentials[0]["groups"]:
            if group["id"] == current_group_id:
                current_group_name = group["name"]
                break
        assert current_group_name == group_name

        # Now unset the current group (set to None)
        unset_payload = {
            "source_type": "tool",
            "source_id": CREDENTIALS_TEST_TOOL,
            "source_version": "test",
            "service_credentials": [{"user_credentials_id": user_credentials_id, "current_group_id": None}],
        }
        response = self._put("/api/users/current/credentials", data=unset_payload, json=True)
        self._assert_status_code_is(response, 204)

        # Verify current group is unset
        list_user_credentials = self._check_credentials_exist()
        assert list_user_credentials[0]["current_group_id"] is None

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_required_credentials_validation(self):
        """Test that required (non-optional) credentials are properly validated."""
        # Test missing required variable
        payload = self._build_credentials_payload()
        payload["service_credential"]["group"]["variables"] = []  # Remove required 'server' variable
        self._provide_user_credentials(payload, status_code=400)

        # Test missing required secret
        payload = self._build_credentials_payload()
        payload["service_credential"]["group"]["secrets"] = [
            {"name": "password", "value": "pass"}  # Remove required 'username' secret
        ]
        self._provide_user_credentials(payload, status_code=400)

        # Test empty required variable
        payload = self._build_credentials_payload()
        payload["service_credential"]["group"]["variables"] = [{"name": "server", "value": ""}]
        self._provide_user_credentials(payload, status_code=400)

        # Test empty required secret
        payload = self._build_credentials_payload()
        payload["service_credential"]["group"]["secrets"] = [
            {"name": "username", "value": ""},  # Empty required secret
            {"name": "password", "value": "pass"},
        ]
        self._provide_user_credentials(payload, status_code=400)

        # Test that optional credentials can be omitted (password is optional)
        payload = self._build_credentials_payload()
        payload["service_credential"]["group"]["secrets"] = [
            {"name": "username", "value": "user"}  # Only required secret, optional 'password' omitted
        ]
        self._provide_user_credentials(payload, status_code=200)

    def _provide_user_credentials(self, payload=None, status_code=200):
        payload = payload or self._build_credentials_payload()
        response = self._post("/api/users/current/credentials", data=payload, json=True)
        self._assert_status_code_is(response, status_code)
        return response.json()

    def _build_credentials_payload(
        self,
        source_type: str = "tool",
        source_id: str = CREDENTIALS_TEST_TOOL,
        source_version: str = "test",
        service_name: str = "service1",
        service_version: str = "1",
        group_name=None,
    ):
        if group_name is None:
            group_name = random_name()

        return {
            "source_type": source_type,
            "source_id": source_id,
            "source_version": source_version,
            "service_credential": {
                "name": service_name,
                "version": service_version,
                "group": {
                    "name": group_name,
                    "variables": [{"name": "server", "value": "http://localhost:8080"}],
                    "secrets": [
                        {"name": "username", "value": "user"},
                        {"name": "password", "value": "pass"},
                    ],
                },
            },
        }

    def _check_credentials_exist(self, source_id: str = CREDENTIALS_TEST_TOOL, num_credentials: int = 1):
        response = self._get(f"/api/users/current/credentials?source_type=tool&source_id={source_id}")
        self._assert_status_code_is(response, 200)
        list_user_credentials = response.json()
        assert len(list_user_credentials) == num_credentials
        if num_credentials > 0:
            assert list_user_credentials[0]["source_id"] == source_id

        return list_user_credentials

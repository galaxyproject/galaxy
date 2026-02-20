from typing import Optional

from galaxy.model.db.user import get_user_by_email
from galaxy.security.vault import UserVaultWrapper
from galaxy_test.base.api_util import random_name
from galaxy_test.base.populators import (
    CredentialsPopulator,
    skip_without_tool,
)
from galaxy_test.driver import integration_util

CREDENTIALS_TEST_TOOL = "secret_tool"
DEFAULT_TOOL_VARIABLES = [{"name": "server", "value": "http://localhost:8080"}]
DEFAULT_TOOL_SECRETS = [{"name": "username", "value": "user"}, {"name": "password", "value": "pass"}]


class TestCredentialsApi(integration_util.IntegrationTestCase, integration_util.ConfiguresDatabaseVault):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)

    def setUp(self):
        super().setUp()
        self.credentials_populator = CredentialsPopulator(self.galaxy_interactor)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_provide_credential(self):
        created_credential_group = self._create_credentials(group_name="default")
        assert created_credential_group["name"] == "default"
        assert len(created_credential_group["variables"]) == 1
        assert len(created_credential_group["secrets"]) == 2

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_anon_users_cannot_provide_credentials(self):
        self._create_credentials(expected_status=403, anon=True)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_list_user_credentials(self):
        self._create_credentials()

        # Check there is at least one credential
        list_user_credentials = self.credentials_populator.list_credentials()
        assert len(list_user_credentials) > 0

        # Check the specific credential exists
        self._check_credentials_exist()

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_other_users_cannot_list_credentials(self):
        self._create_credentials()

        self._check_credentials_exist()

        with self._different_user():
            self._check_credentials_exist(num_credentials=0)

    def test_list_by_source_id_requires_source_type(self):
        self.credentials_populator.list_credentials(source_id=CREDENTIALS_TEST_TOOL, expected_status=400)

    def test_list_unsupported_source_type(self):
        self.credentials_populator.list_credentials(source_type="invalid", expected_status=400)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_add_group_to_credentials(self):
        # Use unique group names to avoid interference from other tests
        initial_group = random_name()

        # First, create initial credentials with a unique group
        self._create_credentials(group_name=initial_group)
        initial_credentials = self._check_credentials_exist()
        assert len(initial_credentials) == 1

        # Should have only our group (plus any leftover groups from other tests)
        groups_before = {group["name"]: group for group in initial_credentials[0]["groups"]}
        assert initial_group in groups_before

        # Create a new group with the same service credentials
        second_group = random_name()
        self._create_credentials(group_name=second_group)

        # Check that both our groups exist
        updated_credentials = self._check_credentials_exist()
        assert len(updated_credentials) == 1

        # Find our specific groups by name
        groups_after = {group["name"]: group for group in updated_credentials[0]["groups"]}
        assert initial_group in groups_after
        assert second_group in groups_after

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_update_credentials_update_time(self):
        created_group = self._create_credentials()
        created_group_id = created_group["id"]

        list_user_credentials = self._check_credentials_exist()
        user_credentials_id = list_user_credentials[0]["id"]

        update_payload = self._build_update_credentials_payload(group_name=random_name())
        group_name_updated_group = self._update_credentials(user_credentials_id, created_group_id, update_payload)
        assert group_name_updated_group["update_time"] > created_group["update_time"]

        update_payload = self._build_update_credentials_payload(variables=[{"name": "server", "value": random_name()}])
        variable_updated_group = self._update_credentials(user_credentials_id, created_group_id, update_payload)
        assert variable_updated_group["update_time"] > group_name_updated_group["update_time"]
        assert variable_updated_group["update_time"] > created_group["update_time"]

        update_payload = self._build_update_credentials_payload(
            secrets=[{"name": "username", "value": random_name()}, {"name": "password", "value": None}]
        )
        secret_updated_group = self._update_credentials(user_credentials_id, created_group_id, update_payload)
        assert secret_updated_group["update_time"] > variable_updated_group["update_time"]
        assert secret_updated_group["update_time"] > group_name_updated_group["update_time"]
        assert secret_updated_group["update_time"] > created_group["update_time"]

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_update_credentials(self):
        # Create initial credentials
        initial_group = self._create_credentials()
        group_id = initial_group["id"]

        list_user_credentials = self._check_credentials_exist()
        user_credentials_id = list_user_credentials[0]["id"]

        # Update only group name
        new_name = random_name()
        result = self._update_credentials(
            user_credentials_id, group_id, self._build_update_credentials_payload(group_name=new_name)
        )
        assert result["name"] == new_name

        # Update only variables
        new_variables = [{"name": "server", "value": "https://new-server.com"}]
        result = self._update_credentials(
            user_credentials_id, group_id, self._build_update_credentials_payload(variables=new_variables)
        )
        assert result["variables"][0]["value"] == "https://new-server.com"

        # Update only secrets
        new_secrets = [{"name": "username", "value": "newuser"}, {"name": "password", "value": "newpass"}]
        result = self._update_credentials(
            user_credentials_id, group_id, self._build_update_credentials_payload(secrets=new_secrets)
        )
        assert any(s["name"] == "username" and s["is_set"] for s in result["secrets"])

        # Update all fields at once
        final_name = random_name()
        final_variables = [{"name": "server", "value": "https://final-server.com"}]
        final_secrets = [{"name": "username", "value": "finaluser"}, {"name": "password", "value": "finalpass"}]
        result = self._update_credentials(
            user_credentials_id,
            group_id,
            self._build_update_credentials_payload(
                group_name=final_name, variables=final_variables, secrets=final_secrets
            ),
        )
        assert result["name"] == final_name
        assert result["variables"][0]["value"] == "https://final-server.com"
        assert any(s["name"] == "username" and s["is_set"] for s in result["secrets"])

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_update_credentials_error_cases(self):
        """Test update error scenarios."""
        group = self._create_credentials()
        group_id = group["id"]

        list_user_credentials = self._check_credentials_exist()
        user_credentials_id = list_user_credentials[0]["id"]

        # Invalid group name - use empty string which should be invalid
        self._update_credentials(
            user_credentials_id, group_id, self._build_update_credentials_payload(group_name=""), status_code=400
        )

        # Missing required variable
        self._update_credentials(
            user_credentials_id, group_id, self._build_update_credentials_payload(variables=[]), status_code=400
        )

        # Missing required secret
        self._update_credentials(
            user_credentials_id,
            group_id,
            self._build_update_credentials_payload(secrets=[{"name": "password", "value": "pass"}]),
            status_code=400,
        )

        # Invalid credential names
        self._update_credentials(
            user_credentials_id,
            group_id,
            self._build_update_credentials_payload(variables=[{"name": "invalid_name", "value": "value"}]),
            status_code=400,
        )
        self._update_credentials(
            user_credentials_id,
            group_id,
            self._build_update_credentials_payload(secrets=[{"name": "invalid_secret", "value": "value"}]),
            status_code=400,
        )

        # Empty required values
        self._update_credentials(
            user_credentials_id,
            group_id,
            self._build_update_credentials_payload(variables=[{"name": "server", "value": ""}]),
            status_code=400,
        )
        self._update_credentials(
            user_credentials_id,
            group_id,
            self._build_update_credentials_payload(
                secrets=[{"name": "username", "value": ""}, {"name": "password", "value": "pass"}]
            ),
            status_code=400,
        )

        # Test non-existent group ID
        self._update_credentials(
            user_credentials_id,
            "f2db41e1fa331b3e",
            self._build_update_credentials_payload(group_name="test"),
            status_code=400,
        )

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_delete_service_credentials(self):
        # Create credentials
        self._create_credentials()

        # Check credentials exist and get the service credentials ID
        credentials_list = self._check_credentials_exist()
        service_credentials_id = credentials_list[0]["id"]

        # Delete the entire service credentials
        self.credentials_populator.delete_service_credentials(service_credentials_id)

        # Check credentials are deleted
        self._check_credentials_exist(num_credentials=0)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_delete_credentials_group(self):
        # Use unique group names to avoid test interference
        initial_group = random_name()
        target_group_name = random_name()

        # Create initial credentials with unique group
        self._create_credentials(group_name=initial_group)

        # Add a new group
        self._create_credentials(group_name=target_group_name)

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
        self.credentials_populator.select_current_group(
            "tool", CREDENTIALS_TEST_TOOL, "test", user_credentials_id, target_group_id
        )

        # Verify it's set as current
        list_user_credentials = self._check_credentials_exist()
        assert list_user_credentials[0]["current_group_id"] == target_group_id

        # Delete the group
        self.credentials_populator.delete_credentials_group(user_credentials_id, target_group_id)

        # Check group is deleted - should only have our initial group left
        list_user_credentials = self._check_credentials_exist()
        groups_after = {group["name"]: group for group in list_user_credentials[0]["groups"]}
        assert target_group_name not in groups_after  # Target group should be deleted
        assert initial_group in groups_after  # Initial group should remain
        assert list_user_credentials[0]["current_group_id"] is None

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_provide_credential_invalid_group(self):
        self._create_credentials(group_name="", expected_status=400)

    def test_invalid_source_type(self):
        self._create_credentials(source_type="invalid_source_type", expected_status=400)

    def test_not_existing_tool(self):
        self._create_credentials(tool_id="nonexistent_tool", expected_status=404)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_not_existing_tool_version(self):
        self._create_credentials(source_version="nonexistent_tool_version", expected_status=404)

    def test_not_existing_service_name(self):
        self._create_credentials(service_name="nonexistent_service", expected_status=404)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_not_existing_service_version(self):
        self._create_credentials(service_version="nonexistent_service_version", expected_status=404)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_invalid_credential_name(self):
        for key in ["variables", "secrets"]:
            payload = self._build_credentials_payload()
            payload["service_credential"]["group"][key][0]["name"] = "invalid_name"
            self.credentials_populator.post_credentials(payload, expected_status=400)

    def test_delete_nonexistent_service_credentials(self):
        self.credentials_populator.delete_service_credentials("f2db41e1fa331b3e", expected_status=400)

    def test_delete_nonexistent_credentials_group(self):
        self.credentials_populator.delete_credentials_group("f2db41e1fa331b3e", "f2db41e1fa331b3e", expected_status=400)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_delete_default_credential_group(self):
        created_user_credentials = self._create_credentials()
        # The new API returns a single ServiceCredentialGroupResponse, not a list
        group_id = created_user_credentials["id"]

        # Get the user credentials to find the service credentials ID
        user_credentials_list = self._check_credentials_exist()
        user_credentials_id = user_credentials_list[0]["id"]

        self.credentials_populator.delete_credentials_group(user_credentials_id, group_id)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_unset_current_group(self):
        # First create credentials with a unique group
        group_name = random_name()
        self._create_credentials(group_name=group_name)

        # Set this group as current
        user_credentials_list = self._check_credentials_exist()
        user_credentials_id = user_credentials_list[0]["id"]
        default_group_id = None
        for group in user_credentials_list[0]["groups"]:
            if group["name"] == group_name:
                default_group_id = group["id"]
                break

        self.credentials_populator.select_current_group(
            "tool", CREDENTIALS_TEST_TOOL, "test", user_credentials_id, default_group_id
        )

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
        self.credentials_populator.select_current_group(
            "tool", CREDENTIALS_TEST_TOOL, "test", user_credentials_id, None
        )

        # Verify current group is unset
        list_user_credentials = self._check_credentials_exist()
        assert list_user_credentials[0]["current_group_id"] is None

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_required_credentials_validation(self):
        """Test that required (non-optional) credentials are properly validated."""
        # Test missing required variable
        self._create_credentials(variables=[], expected_status=400)

        # Test missing required secret
        self._create_credentials(secrets=[{"name": "password", "value": "pass"}], expected_status=400)

        # Test empty required variable
        self._create_credentials(variables=[{"name": "server", "value": ""}], expected_status=400)

        # Test empty required secret
        self._create_credentials(
            secrets=[
                {"name": "username", "value": ""},  # Empty required secret
                {"name": "password", "value": "pass"},
            ],
            expected_status=400,
        )

        # Test that optional credentials can be omitted (password is optional)
        self._create_credentials(
            secrets=[{"name": "username", "value": "user"}],  # Only required secret, optional 'password' omitted
            expected_status=200,
        )

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_vault_integration(self):
        test_user_email = "user@vault.test"
        with self._different_user(test_user_email):
            payload = self._build_credentials_payload()
            self.credentials_populator.post_credentials(payload)

            credentials_list = self._check_credentials_exist()
            assert len(credentials_list) == 1
            group = credentials_list[0]["groups"][0]

            # Check that secrets are stored in the vault
            for secret in DEFAULT_TOOL_SECRETS:
                vault_ref = self._get_vault_ref(payload, group["id"], secret["name"])
                expected_value = secret["value"]
                self._check_vault_entry_exists(test_user_email, vault_ref, expected_value)

            # Delete the credentials group
            user_credentials_id = credentials_list[0]["id"]
            group_id = group["id"]
            self.credentials_populator.delete_credentials_group(user_credentials_id, group_id)

            # Check that secrets are removed from the vault
            for secret in DEFAULT_TOOL_SECRETS:
                vault_ref = self._get_vault_ref(payload, group["id"], secret["name"])
                self._check_vault_entry_exists(test_user_email, vault_ref, should_exist=False)

    @skip_without_tool(CREDENTIALS_TEST_TOOL)
    def test_list_credentials_with_missing_tool(self):
        # Create credentials for the test tool
        payload = self._build_credentials_payload()
        self.credentials_populator.post_credentials(payload)

        # Verify credentials exist normally
        credentials_list = self._check_credentials_exist()
        assert len(credentials_list) == 1
        user_credentials_id = credentials_list[0]["id"]

        # Save the tool reference before removing it
        tool = self._app.toolbox.get_tool(CREDENTIALS_TEST_TOOL)
        assert tool is not None, f"Tool {CREDENTIALS_TEST_TOOL} should be available before removal"

        try:
            # Remove the tool to simulate it being unavailable
            # Use remove_from_panel=False to keep restoration simple
            self._app.toolbox.remove_tool_by_id(CREDENTIALS_TEST_TOOL, remove_from_panel=False)

            # Verify tool is actually removed
            assert self._app.toolbox.get_tool(CREDENTIALS_TEST_TOOL) is None

            # Test 1: List credentials with include_definition=True
            credentials_with_definition = self.credentials_populator.list_credentials(include_definition=True)

            assert len(credentials_with_definition) == 1
            credential = credentials_with_definition[0]

            # Check that the credential still has basic information
            assert credential["id"] == user_credentials_id
            assert credential["source_id"] == CREDENTIALS_TEST_TOOL
            assert credential["source_type"] == "tool"

            # Check that the fallback definition was provided
            assert "definition" in credential
            definition = credential["definition"]
            assert definition["name"] == payload["service_credential"]["name"]
            assert definition["version"] == payload["service_credential"]["version"]
            assert definition["description"] == ""
            assert definition["label"] == ""
            assert definition["optional"] is False
            assert definition["variables"] == []
            assert definition["secrets"] == []

            # Verify that groups are still present and accessible
            assert len(credential["groups"]) > 0

            # Test 2: List credentials without include_definition
            credentials_without_definition = self.credentials_populator.list_credentials()

            assert len(credentials_without_definition) == 1
            credential_no_def = credentials_without_definition[0]

            # Should not have definition field when not requested
            assert "definition" not in credential_no_def
            assert credential_no_def["id"] == user_credentials_id
            assert len(credential_no_def["groups"]) > 0
        finally:
            # Restore the tool to avoid affecting other tests
            if tool is not None:
                self._app.toolbox.register_tool(tool)

    def _update_credentials(self, user_credentials_id, group_id, payload=None, status_code=200):
        payload = payload or self._build_update_credentials_payload()
        return self.credentials_populator.update_credentials_group(
            user_credentials_id, group_id, payload, expected_status=status_code
        )

    def _build_credentials_payload(self, **kwargs):
        kwargs.setdefault("tool_id", CREDENTIALS_TEST_TOOL)
        kwargs.setdefault("variables", DEFAULT_TOOL_VARIABLES)
        kwargs.setdefault("secrets", DEFAULT_TOOL_SECRETS)
        return self.credentials_populator.build_credentials_payload(**kwargs)

    def _create_credentials(self, **kwargs):
        kwargs.setdefault("tool_id", CREDENTIALS_TEST_TOOL)
        kwargs.setdefault("variables", DEFAULT_TOOL_VARIABLES)
        kwargs.setdefault("secrets", DEFAULT_TOOL_SECRETS)
        return self.credentials_populator.create_credentials(**kwargs)

    def _build_update_credentials_payload(
        self,
        group_name=None,
        variables=None,
        secrets=None,
    ):
        update_payload = self._build_credentials_payload()["service_credential"]["group"]
        if group_name is not None:
            update_payload["name"] = group_name
        if variables is not None:
            update_payload["variables"] = variables
        if secrets is not None:
            update_payload["secrets"] = secrets
        return update_payload

    def _check_credentials_exist(self, source_id: str = CREDENTIALS_TEST_TOOL, num_credentials: int = 1):
        list_user_credentials = self.credentials_populator.list_credentials(source_type="tool", source_id=source_id)
        assert len(list_user_credentials) == num_credentials
        if num_credentials > 0:
            assert list_user_credentials[0]["source_id"] == source_id

        return list_user_credentials

    def _check_vault_entry_exists(
        self, user_email: str, vault_ref: str, expected_value: Optional[str] = None, should_exist=True
    ):
        app = self._app
        user = get_user_by_email(app.model.session, user_email)
        user_vault = UserVaultWrapper(app.vault, user)
        stored_value = user_vault.read_secret(vault_ref)
        if should_exist:
            assert (
                stored_value == expected_value
            ), f"Expected vault entry '{vault_ref}' to have value '{expected_value}', got '{stored_value}'"
        else:
            assert (
                stored_value is None
                # Ideally we would check for None, but some vault implementations write an empty string when deleting
                or stored_value == ""
            ), f"Expected vault entry '{vault_ref}' to not exist, but found value '{stored_value}'"

    def _get_vault_ref(self, payload: dict, group_id: str, secret_name: str) -> str:
        decoded_group_id = self._app.security.decode_id(group_id)
        return f"{payload['source_type']}|{payload['source_id']}|{payload['service_credential']['name']}|{payload['service_credential']['version']}|{decoded_group_id}|{secret_name}"

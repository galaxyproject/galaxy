from typing import (
    cast,
    Optional,
)

from sqlalchemy import select

from galaxy.managers.landing import LandingRequestModel
from galaxy.model import (
    ToolLandingRequest as ToolLandingRequestModel,
    WorkflowLandingRequest as WorkflowLandingRequestModel,
)
from galaxy.schema.fetch_data import (
    CreateDataLandingPayload,
    DataLandingRequestState,
)
from galaxy.schema.schema import (
    CreateWorkflowLandingRequestPayload,
    ToolLandingRequest,
)
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util

TEST_URL = "base64://eyJ0ZXN0IjogInRlc3QifQ=="  # base64 encoded {"test": "test"}

# URL headers configuration for tests - allows both sensitive and non-sensitive headers
ALLOW_URL_HEADERS_CONF = """
patterns:
  # Match all URLs (including base64://) for testing
  - url_pattern: "^.*"
    headers:
      # Sensitive headers - will be encrypted when vault is configured
      - name: Authorization
        sensitive: true
      - name: X-API-Key
        sensitive: true
      # Non-sensitive headers
      - name: Content-Type
        sensitive: false
      - name: Accept
        sensitive: false
      - name: Accept-Language
        sensitive: false
      - name: Accept-Encoding
        sensitive: false
      - name: Cache-Control
        sensitive: false
      - name: X-Custom-Header
        sensitive: false
"""


class BaseLandingRequestTest(integration_util.IntegrationTestCase, integration_util.ConfigureAllowedUrlHeaders):
    """Base class with common setup for landing request tests."""

    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def _create_data_item_with_headers(self, headers: dict[str, str], url: str = TEST_URL) -> dict:
        """Create a data item with specified headers."""
        return {
            "src": "url",
            "url": url,
            "ext": "txt",
            "deferred": False,
            "headers": headers,
        }

    def _create_data_landing_request_state(
        self, headers: dict[str, str], url: str = TEST_URL
    ) -> DataLandingRequestState:
        """Create a DataLandingRequestState with specified headers."""
        return DataLandingRequestState(
            targets=[
                {
                    "destination": {"type": "hdas"},
                    "items": [self._create_data_item_with_headers(headers, url)],
                }
            ],
        )

    def _create_workflow_input_with_headers(
        self, headers: dict[str, str], input_name: str = "WorkflowInput1", url: str = TEST_URL
    ) -> dict[str, dict]:
        """Create a workflow input with specified headers."""
        return {
            input_name: {
                "src": "url",
                "url": url,
                "ext": "txt",
                "deferred": False,
                "headers": headers,
            }
        }

    def _assert_headers_match(self, actual_headers: dict[str, str], expected_headers: dict[str, str]) -> None:
        """Assert that headers match expected values."""
        for key, expected_value in expected_headers.items():
            assert (
                actual_headers[key] == expected_value
            ), f"Header {key} mismatch: expected {expected_value}, got {actual_headers.get(key)}"

    def _extract_data_landing_headers(self, tool_landing: ToolLandingRequest) -> dict[str, str]:
        """Extract headers from a tool landing response."""
        request_state = tool_landing.request_state
        assert request_state, "Request state is None"
        request_json = request_state["request_json"]
        assert request_json, "Request JSON is None"
        targets = request_json["targets"]
        assert targets and len(targets) == 1, "Expected exactly one target"
        target = targets[0]
        assert "elements" in target and target["elements"], "No elements found in target"
        assert len(target["elements"]) == 1, "Expected exactly one element"
        element = target["elements"][0]
        assert "headers" in element, "No headers found in element"
        return element["headers"]

    def _verify_headers_encrypted_in_db(
        self, landing_request_uuid: str, expect_not_to_find: list[str], model_class: type[LandingRequestModel]
    ):
        """Verify that sensitive headers are stored encrypted in the database."""
        landing_request = self._get_landing_request_from_db(landing_request_uuid, model_class)
        assert (
            landing_request is not None
        ), f"{model_class.__name__} with UUID {landing_request_uuid} not found in database"
        request_state_json = landing_request.request_state
        assert request_state_json is not None, "Request state is None in database"
        request_state_json_str = str(request_state_json)

        for header_value in expect_not_to_find:
            assert header_value not in request_state_json_str, f"Sensitive header {header_value} found in plain text"

    def _get_landing_request_from_db(
        self, uuid: str, model_class: type[LandingRequestModel]
    ) -> Optional[LandingRequestModel]:
        """Get a landing request from the database by UUID."""
        session = self._app.model.session
        stmt = select(model_class).where(model_class.uuid == uuid)
        return cast(Optional[LandingRequestModel], session.execute(stmt).scalar_one_or_none())

    def _create_and_make_public_workflow(self, workflow_name: str) -> str:
        """Create a simple workflow and make it public."""
        workflow_id = self.workflow_populator.simple_workflow(workflow_name)
        self.workflow_populator.make_public(workflow_id)
        return workflow_id


class TestLandingRequestsIntegration(BaseLandingRequestTest, integration_util.ConfiguresDatabaseVault):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)
        cls._configure_allowed_url_headers(ALLOW_URL_HEADERS_CONF, config)

    def test_data_landing_with_encrypted_headers(self):
        """Test that sensitive headers are encrypted in the vault when stored in landing requests.

        This test verifies that headers containing sensitive information like authorization tokens
        are encrypted using Galaxy's vault system instead of being stored in plain text in the
        database. Headers are automatically detected and encrypted based on their names.
        """
        # Create test headers with both sensitive and non-sensitive values
        headers = {
            "Authorization": "Bearer data-test-token-should-be-encrypted",
            "X-API-Key": "data-test-api-key-123456",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Custom-Header": "custom-value",
        }

        # Create and execute data landing request
        request_state = self._create_data_landing_request_state(headers)
        payload = CreateDataLandingPayload(request_state=request_state, public=True)
        response = self.dataset_populator.create_data_landing(payload)
        assert response.tool_id == "__DATA_FETCH__"

        # Verify headers are preserved after decryption
        tool_landing = self.dataset_populator.use_tool_landing(response.uuid)
        actual_headers = self._extract_data_landing_headers(tool_landing)
        self._assert_headers_match(actual_headers, headers)

        # Verify that sensitive headers are stored encrypted in the database
        sensitive_values = ["Bearer data-test-token-should-be-encrypted", "data-test-api-key-123456"]
        self._verify_headers_encrypted_in_db(str(response.uuid), sensitive_values, ToolLandingRequestModel)

    def test_workflow_landing_with_encrypted_headers(self):
        """Test that sensitive headers are encrypted in workflow landing requests.

        This test verifies that headers containing sensitive information like authorization tokens
        are encrypted using Galaxy's vault system when workflow landing requests contain URL fetch
        steps with headers.
        """
        # Create test headers for workflow inputs
        input1_headers = {
            "Authorization": "Bearer workflow-test-token-should-be-encrypted",
            "X-API-Key": "workflow-test-api-key-123456",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        input2_headers = {
            "Authorization": "Bearer workflow-test-token-should-be-encrypted",
            "X-API-Key": "workflow-test-api-key-123456",
            "Accept-Language": "en-US",
            "X-Custom-Header": "custom-value",
        }

        # Create workflow request state with multiple inputs
        workflow_request_state = {}
        workflow_request_state.update(self._create_workflow_input_with_headers(input1_headers, "WorkflowInput1"))
        workflow_request_state.update(self._create_workflow_input_with_headers(input2_headers, "WorkflowInput2"))

        # Create workflow and landing request
        workflow_id = self._create_and_make_public_workflow("test_landing_encrypted_headers")
        payload = CreateWorkflowLandingRequestPayload(
            workflow_id=workflow_id,
            workflow_target_type="stored_workflow",
            request_state=workflow_request_state,
            public=True,
        )

        # Create and retrieve workflow landing request
        workflow_landing = self.dataset_populator.create_workflow_landing(payload)
        assert workflow_landing.workflow_target_type == "stored_workflow"

        retrieved_workflow_landing = self.dataset_populator.use_workflow_landing(workflow_landing.uuid)
        request_state = retrieved_workflow_landing.request_state

        # Verify headers are preserved in both workflow inputs
        assert "WorkflowInput1" in request_state and "WorkflowInput2" in request_state
        self._assert_headers_match(request_state["WorkflowInput1"]["headers"], input1_headers)
        self._assert_headers_match(request_state["WorkflowInput2"]["headers"], input2_headers)

        # Verify that sensitive headers are stored encrypted in the database
        sensitive_values = ["Bearer workflow-test-token-should-be-encrypted", "workflow-test-api-key-123456"]
        self._verify_headers_encrypted_in_db(str(workflow_landing.uuid), sensitive_values, WorkflowLandingRequestModel)


class TestLandingRequestsWithoutVaultIntegration(BaseLandingRequestTest):
    """Test landing requests when headers are configured but vault is not configured.

    This class tests the behavior when headers configuration exists but no vault is configured.
    When sensitive headers are present, the system should fail because it cannot encrypt them.
    """

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # Configure headers but NOT vault - this tests the vault requirement for sensitive headers
        cls._configure_allowed_url_headers(ALLOW_URL_HEADERS_CONF, config)

    def test_data_landing_fails_without_vault_when_sensitive_headers_present(self):
        """Test that data landing requests fail when vault is not configured but sensitive headers are present.

        This test verifies that when sensitive headers (like Authorization, API keys, etc.) are present
        in a landing request but no vault is configured, the system fails with a 500 error rather than
        storing the sensitive information in plain text in the database.
        """
        # Create headers with sensitive values
        headers = {
            "Authorization": "Bearer no-vault-test-token-should-fail",
            "X-API-Key": "no-vault-test-api-key-should-fail",
            "Accept": "application/json",
        }

        # Create data landing request with sensitive headers
        request_state = self._create_data_landing_request_state(headers)
        payload = CreateDataLandingPayload(request_state=request_state, public=True)

        # Should return 500 status code when trying to create the landing request
        # because sensitive headers are present but vault is not configured
        response = self.dataset_populator.create_landing_raw(payload, "data")
        assert response.status_code == 500

    def test_data_landing_succeeds_without_vault_when_no_sensitive_headers(self):
        """Test that data landing requests succeed when vault is not configured but no sensitive headers are present.

        This test verifies that when only non-sensitive headers are present in a landing request
        and no vault is configured, the system works normally since encryption is not required.
        """
        # Create only non-sensitive headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Custom-Header": "custom-value",
        }

        # Create data landing request with only non-sensitive headers
        request_state = self._create_data_landing_request_state(headers)
        payload = CreateDataLandingPayload(request_state=request_state, public=True)

        # Should succeed because no sensitive headers are present
        response = self.dataset_populator.create_data_landing(payload)
        assert response.tool_id == "__DATA_FETCH__"

        # Verify we can retrieve the landing request and headers are preserved
        tool_landing = self.dataset_populator.use_tool_landing(response.uuid)
        actual_headers = self._extract_data_landing_headers(tool_landing)
        self._assert_headers_match(actual_headers, headers)

    def test_workflow_landing_fails_without_vault_when_sensitive_headers_present(self):
        """Test that workflow landing requests fail when vault is not configured but sensitive headers are present."""
        # Create workflow input with sensitive headers
        headers = {
            "Authorization": "Bearer workflow-no-vault-token-should-fail",
            "X-API-Key": "workflow-no-vault-api-key-should-fail",
            "Accept": "application/json",
        }
        workflow_request_state = self._create_workflow_input_with_headers(headers)

        # Create workflow and landing request
        workflow_id = self._create_and_make_public_workflow("test_landing_no_vault")
        payload = CreateWorkflowLandingRequestPayload(
            workflow_id=workflow_id,
            workflow_target_type="stored_workflow",
            request_state=workflow_request_state,
            public=True,
        )

        # Should return 500 status code when trying to create the workflow landing request
        # because sensitive headers are present but vault is not configured
        create_url = "workflow_landings"
        json = payload.model_dump(mode="json")
        response = self.dataset_populator._post(create_url, json, json=True, anon=True)
        assert response.status_code == 500


class TestLandingRequestsWithoutHeadersConfigIntegration(BaseLandingRequestTest):
    """Test landing requests when no headers configuration exists.

    This class tests the behavior when no URL headers configuration file is present.
    The system should fail fast with any headers (sensitive or not) because headers
    require explicit configuration to be allowed.
    """

    def test_data_landing_fails_without_config(self):
        """Test that data landing requests fail when no URL headers configuration exists.

        This test verifies the fail-fast behavior: when no URL headers configuration file
        exists, ANY attempt to use headers (sensitive or not) will fail immediately with
        a clear error message, rather than silently allowing or denying headers.
        """
        # Create only non-sensitive headers
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Custom-Header": "custom-value",
        }

        # Create data landing request with headers
        request_state = self._create_data_landing_request_state(headers)
        payload = CreateDataLandingPayload(request_state=request_state, public=True)

        # Should fail with 403 because no URL headers configuration is available (fail-fast)
        response = self.dataset_populator.create_landing_raw(payload, "data")
        assert response.status_code == 403
        assert "No URL headers configuration is available" in response.json()["err_msg"]

    def test_workflow_landing_fails_without_config(self):
        """Test that workflow landing requests fail when no URL headers configuration exists.

        This test verifies the fail-fast behavior for workflow landings: when no URL headers
        configuration file exists, any attempt to use headers will fail immediately.
        """
        # Create workflow input with headers
        headers = {
            "Authorization": "Bearer workflow-no-vault-token-should-fail",
            "X-API-Key": "workflow-no-vault-api-key-should-fail",
            "Accept": "application/json",
        }
        workflow_request_state = self._create_workflow_input_with_headers(headers)

        # Create workflow and landing request
        workflow_id = self._create_and_make_public_workflow("test_landing_no_config")
        payload = CreateWorkflowLandingRequestPayload(
            workflow_id=workflow_id,
            workflow_target_type="stored_workflow",
            request_state=workflow_request_state,
            public=True,
        )

        # Should return 403 status code when trying to create the workflow landing request
        # because no URL headers configuration is available
        create_url = "workflow_landings"
        json = payload.model_dump(mode="json")
        response = self.dataset_populator._post(create_url, json, json=True, anon=True)
        assert response.status_code == 403
        assert "No URL headers configuration is available" in response.json()["err_msg"]

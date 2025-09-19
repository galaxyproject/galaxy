from typing import (
    cast,
    Optional,
    Type,
)

from sqlalchemy import select

from galaxy.managers.landing import LandingRequestModel
from galaxy.model import (
    ToolLandingRequest,
    WorkflowLandingRequest,
)
from galaxy.schema.fetch_data import (
    CreateDataLandingPayload,
    DataLandingRequestState,
)
from galaxy.schema.schema import CreateWorkflowLandingRequestPayload
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util


class TestLandingRequestsIntegration(integration_util.IntegrationTestCase, integration_util.ConfiguresDatabaseVault):
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_data_landing_with_encrypted_headers(self):
        """Test that sensitive headers are encrypted in the vault when stored in landing requests.

        This test verifies that headers containing sensitive information like authorization tokens
        are encrypted using Galaxy's vault system instead of being stored in plain text in the
        database. Headers are automatically detected and encrypted based on their names.
        """
        authorization_secret = "Bearer secret-token-should-be-encrypted"
        x_api_key_secret = "secret-api-key-123456"
        data_landing_request_state = DataLandingRequestState(
            targets=[
                {
                    "destination": {"type": "hdas"},
                    "items": [
                        {
                            "src": "url",
                            "url": "base64://eyJ0ZXN0IjogInRlc3QifQ==",  # base64 encoded {"test": "test"}
                            "ext": "txt",
                            "deferred": False,
                            "headers": {
                                "Authorization": authorization_secret,
                                "X-API-Key": x_api_key_secret,
                                "User-Agent": "Galaxy-Test/1.0",  # Non-sensitive header
                                "X-Custom-Header": "custom-value",  # Non-sensitive header
                            },
                        }
                    ],
                }
            ],
        )
        payload = CreateDataLandingPayload(request_state=data_landing_request_state, public=True)
        response = self.dataset_populator.create_data_landing(payload)
        assert response.tool_id == "__DATA_FETCH__"

        tool_landing = self.dataset_populator.use_tool_landing(response.uuid)
        request_state = tool_landing.request_state
        assert request_state
        request_json = request_state["request_json"]
        assert request_json
        targets = request_json["targets"]
        assert targets
        assert len(targets) == 1
        target = targets[0]
        assert "elements" in target
        assert target["elements"]
        assert len(target["elements"]) == 1

        # Verify that headers are preserved in the request
        element = target["elements"][0]
        assert "headers" in element
        headers = element["headers"]

        # Sensitive headers should be decrypted and available
        assert headers["Authorization"] == authorization_secret
        assert headers["X-API-Key"] == x_api_key_secret
        # Non-sensitive headers should remain as-is
        assert headers["User-Agent"] == "Galaxy-Test/1.0"
        assert headers["X-Custom-Header"] == "custom-value"

        # Verify that sensitive headers are stored encrypted in the database
        self._verify_headers_encrypted_in_db(
            str(response.uuid),
            expect_not_to_find=[authorization_secret, x_api_key_secret],
            model_class=ToolLandingRequest,
        )

    def test_workflow_landing_with_encrypted_headers(self):
        """Test that sensitive headers are encrypted in workflow landing requests.

        This test verifies that headers containing sensitive information like authorization tokens
        are encrypted using Galaxy's vault system when workflow landing requests contain URL fetch
        steps with headers.
        """
        authorization_secret = "Bearer secret-workflow-token-encrypted"
        x_api_key_secret = "workflow-api-key-987654"

        # Create a workflow landing request with headers in the request_state
        workflow_request_state = {
            "WorkflowInput1": {
                "src": "url",
                "url": "base64://eyJ3b3JrZmxvdyI6ICJ0ZXN0In0=",  # base64 encoded {"workflow": "test"}
                "ext": "txt",
                "deferred": False,
                "headers": {
                    "Authorization": authorization_secret,
                    "X-API-Key": x_api_key_secret,
                    "User-Agent": "Galaxy-Workflow-Test/1.0",  # Non-sensitive header
                    "Content-Type": "application/json",  # Non-sensitive header
                },
            },
            "WorkflowInput2": {
                "src": "url",
                "url": "base64://eyJ3b3JrZmxvdzIiOiAidGVzdCJ9",  # base64 encoded {"workflow2": "test"}
                "ext": "txt",
                "deferred": False,
                "headers": {
                    "Authorization": authorization_secret,  # Same sensitive header
                    "X-Custom-Header": "custom-value",  # Non-sensitive header
                },
            },
        }

        # Create a simple workflow and make it public
        workflow_id = self.workflow_populator.simple_workflow("test_landing_encrypted_headers")
        self.workflow_populator.make_public(workflow_id)

        payload = CreateWorkflowLandingRequestPayload(
            workflow_id=workflow_id,
            workflow_target_type="stored_workflow",
            request_state=workflow_request_state,
            public=True,
        )

        # Create workflow landing request - headers should be encrypted
        workflow_landing = self.dataset_populator.create_workflow_landing(payload)
        assert workflow_landing.workflow_target_type == "stored_workflow"

        # Use the workflow landing request - headers should be decrypted
        retrieved_workflow_landing = self.dataset_populator.use_workflow_landing(workflow_landing.uuid)
        request_state = retrieved_workflow_landing.request_state

        # Verify that headers are preserved in both workflow inputs
        assert "WorkflowInput1" in request_state
        assert "WorkflowInput2" in request_state

        # Check WorkflowInput1 headers
        input1_headers = request_state["WorkflowInput1"]["headers"]
        assert input1_headers["Authorization"] == authorization_secret
        assert input1_headers["X-API-Key"] == x_api_key_secret
        assert input1_headers["User-Agent"] == "Galaxy-Workflow-Test/1.0"
        assert input1_headers["Content-Type"] == "application/json"

        # Check WorkflowInput2 headers
        input2_headers = request_state["WorkflowInput2"]["headers"]
        assert input2_headers["Authorization"] == authorization_secret
        assert input2_headers["X-Custom-Header"] == "custom-value"

        # Verify that sensitive headers are stored encrypted in the database
        self._verify_headers_encrypted_in_db(
            str(workflow_landing.uuid),
            expect_not_to_find=[authorization_secret, x_api_key_secret],
            model_class=WorkflowLandingRequest,
        )

    def _verify_headers_encrypted_in_db(
        self, landing_request_uuid: str, expect_not_to_find: list[str], model_class: Type[LandingRequestModel]
    ):
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
        self, uuid: str, model_class: Type[LandingRequestModel]
    ) -> Optional[LandingRequestModel]:
        session = self._app.model.session
        stmt = select(model_class).where(model_class.uuid == uuid)
        return cast(Optional[LandingRequestModel], session.execute(stmt).scalar_one_or_none())

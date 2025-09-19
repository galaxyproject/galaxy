from sqlalchemy import select

from galaxy.model import ToolLandingRequest
from galaxy.schema.fetch_data import (
    CreateDataLandingPayload,
    DataLandingRequestState,
)
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class TestLandingRequestsIntegration(integration_util.IntegrationTestCase, integration_util.ConfiguresDatabaseVault):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_database_vault(config)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

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
        )

    def _verify_headers_encrypted_in_db(self, landing_request_uuid: str, expect_not_to_find: list[str]):
        landing_request = self._get_landing_request_from_db(landing_request_uuid)
        assert landing_request is not None, "Landing request not found in database"
        request_state_json = landing_request.request_state
        assert request_state_json is not None, "Request state is None in database"
        request_state_json_str = str(request_state_json)

        # Check that sensitive headers are not present in plain text
        for header_name in expect_not_to_find:
            assert header_name not in request_state_json_str, f"Sensitive header {header_name} found in plain text"

    def _get_landing_request_from_db(self, uuid: str):
        session = self._app.model.session
        stmt = select(ToolLandingRequest).where(ToolLandingRequest.uuid == uuid)
        return session.execute(stmt).scalar_one_or_none()

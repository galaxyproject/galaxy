"""The built-in MCP server answers at its configured endpoint.

Regression tests for https://github.com/galaxyproject/galaxy/issues/23507: the
endpoint was unreachable without a trailing slash, and every request failed
when Galaxy was served under a URL prefix.
"""

import json

import requests

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase


def mcp_request(url: str, method: str, params: dict, headers: dict | None = None) -> dict:
    """POST one JSON-RPC request to a Streamable HTTP endpoint and return its ``result``."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    request_headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    request_headers.update(headers or {})
    response = requests.post(url, json=payload, headers=request_headers, allow_redirects=False)
    response.raise_for_status()
    if response.headers["content-type"].startswith("application/json"):
        body = response.json()
    else:
        data_lines = [line[len("data:") :].strip() for line in response.text.splitlines() if line.startswith("data:")]
        assert data_lines, response.text
        body = json.loads(data_lines[0])
    return body["result"]


def mcp_server_info(url: str) -> dict:
    """Return ``serverInfo`` from a JSON-RPC initialize against a Streamable HTTP endpoint."""
    params = {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "galaxy-integration-test", "version": "0"},
    }
    return mcp_request(url, "initialize", params)["serverInfo"]


class TestMCPEndpoint(IntegrationTestCase):
    mcp_server_path = "/api/mcp"
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["enable_mcp_server"] = True
        config["mcp_server_path"] = cls.mcp_server_path

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_endpoint_without_trailing_slash(self) -> None:
        assert mcp_server_info(f"{self.url}{self.mcp_server_path.strip('/')}")["name"] == "Galaxy"

    def test_endpoint_with_trailing_slash(self) -> None:
        assert mcp_server_info(f"{self.url}{self.mcp_server_path.strip('/')}/")["name"] == "Galaxy"

    def test_galaxy_api_still_accessible(self) -> None:
        response = requests.get(f"{self.url}api/version", allow_redirects=False)
        assert response.status_code == 200
        assert "version_major" in response.json()

    def test_run_tool_refuses_protected_tools(self) -> None:
        # __DATA_FETCH__ trusts its request_json, so it is only reachable through the fetch route
        history_id = self.dataset_populator.new_history()
        inputs = {"request_version": "1", "request_json": "{}", "file_count": "0"}
        result = mcp_request(
            f"{self.url}{self.mcp_server_path.strip('/')}",
            "tools/call",
            {
                "name": "run_tool",
                "arguments": {
                    "history_id": history_id,
                    "tool_id": "__DATA_FETCH__",
                    "inputs": inputs,
                    "api_key": self.galaxy_interactor.api_key,
                },
            },
        )
        assert result.get("isError"), result
        assert "must use alternative endpoint" in result["content"][0]["text"], result


class TestMCPEndpointWithUrlPrefix(TestMCPEndpoint):
    """The same endpoints, with Galaxy served under a URL prefix."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["galaxy_url_prefix"] = "/galaxypf"


class TestMCPEndpointWithCustomPath(TestMCPEndpointWithUrlPrefix):
    mcp_server_path = "/custom/protocol/"

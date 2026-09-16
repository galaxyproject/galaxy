"""The built-in MCP server answers at its configured endpoint.

Regression tests for https://github.com/galaxyproject/galaxy/issues/23507: the
endpoint was unreachable without a trailing slash, and every request failed
when Galaxy was served under a URL prefix.
"""

import json

import requests

from galaxy_test.driver.integration_util import IntegrationTestCase


def mcp_server_info(url: str) -> dict:
    """Return ``serverInfo`` from a JSON-RPC initialize against a Streamable HTTP endpoint."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "galaxy-integration-test", "version": "0"},
        },
    }
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, allow_redirects=False)
    response.raise_for_status()
    if response.headers["content-type"].startswith("application/json"):
        body = response.json()
    else:
        data_lines = [line[len("data:") :].strip() for line in response.text.splitlines() if line.startswith("data:")]
        assert data_lines, response.text
        body = json.loads(data_lines[0])
    return body["result"]["serverInfo"]


class TestMCPEndpoint(IntegrationTestCase):
    mcp_server_path = "/api/mcp"

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["enable_mcp_server"] = True
        config["mcp_server_path"] = cls.mcp_server_path

    def test_endpoint_without_trailing_slash(self) -> None:
        assert mcp_server_info(f"{self.url}{self.mcp_server_path.strip('/')}")["name"] == "Galaxy"

    def test_endpoint_with_trailing_slash(self) -> None:
        assert mcp_server_info(f"{self.url}{self.mcp_server_path.strip('/')}/")["name"] == "Galaxy"

    def test_galaxy_api_still_accessible(self) -> None:
        response = requests.get(f"{self.url}api/version", allow_redirects=False)
        assert response.status_code == 200
        assert "version_major" in response.json()


class TestMCPEndpointWithUrlPrefix(TestMCPEndpoint):
    """The same endpoints, with Galaxy served under a URL prefix."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["galaxy_url_prefix"] = "/galaxypf"


class TestMCPEndpointWithCustomPath(TestMCPEndpointWithUrlPrefix):
    mcp_server_path = "/custom/protocol/"

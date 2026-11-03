"""The built-in MCP server answers at its configured endpoint.

Regression tests for https://github.com/galaxyproject/galaxy/issues/23507: the
endpoint was unreachable without a trailing slash, and every request failed
when Galaxy was served under a URL prefix.
"""

import json

import requests

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


class TestMCPApiKey(IntegrationTestCase):
    """Tools accept the API key from an ``x-api-key`` header as well as the ``api_key`` argument."""

    mcp_server_path = "/api/mcp"

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["enable_mcp_server"] = True
        config["mcp_server_path"] = cls.mcp_server_path

    @property
    def _mcp_url(self) -> str:
        return f"{self.url}{self.mcp_server_path.strip('/')}"

    def _call_tool(self, name: str, arguments: dict, headers: dict | None = None) -> dict:
        return mcp_request(self._mcp_url, "tools/call", {"name": name, "arguments": arguments}, headers)

    def _email_from_get_user(self, result: dict) -> str:
        assert not result.get("isError"), result
        return json.loads(result["content"][0]["text"])["email"]

    def _error_text(self, result: dict) -> str:
        assert result.get("isError"), result
        return result["content"][0]["text"]

    def test_api_key_not_required_in_tool_schemas(self) -> None:
        tools = mcp_request(self._mcp_url, "tools/list", {})["tools"]
        assert tools
        for tool in tools:
            assert "api_key" in tool["inputSchema"].get("properties", {}), tool["name"]
            assert "api_key" not in tool["inputSchema"].get("required", []), tool["name"]

    def test_header_only(self) -> None:
        _, key = self._setup_user_get_key("mcp-header-only@bx.psu.edu")
        result = self._call_tool("get_user", {}, headers={"X-API-Key": key})
        assert self._email_from_get_user(result) == "mcp-header-only@bx.psu.edu"

    def test_argument_only(self) -> None:
        _, key = self._setup_user_get_key("mcp-argument-only@bx.psu.edu")
        result = self._call_tool("get_user", {"api_key": key})
        assert self._email_from_get_user(result) == "mcp-argument-only@bx.psu.edu"

    def test_header_wins_over_argument(self) -> None:
        _, header_key = self._setup_user_get_key("mcp-header-wins@bx.psu.edu")
        _, argument_key = self._setup_user_get_key("mcp-argument-ignored@bx.psu.edu")
        result = self._call_tool("get_user", {"api_key": argument_key}, headers={"x-api-key": header_key})
        assert self._email_from_get_user(result) == "mcp-header-wins@bx.psu.edu"

    def test_empty_argument_falls_back_to_header(self) -> None:
        _, other_key = self._setup_user_get_key("mcp-header-fallback@bx.psu.edu")
        result = self._call_tool("get_user", {"api_key": ""}, headers={"x-api-key": other_key})
        assert self._email_from_get_user(result) == "mcp-header-fallback@bx.psu.edu"

    def test_no_key(self) -> None:
        error = self._error_text(self._call_tool("get_user", {}))
        assert "x-api-key" in error
        assert "exposes the key to the model provider" in error

    def test_invalid_header_key(self) -> None:
        result = self._call_tool("get_user", {}, headers={"x-api-key": "not-a-real-key"})
        assert "API key is not valid" in self._error_text(result)

    def test_invalid_header_key_with_valid_argument(self) -> None:
        _, argument_key = self._setup_user_get_key("mcp-argument-not-used@bx.psu.edu")
        result = self._call_tool("get_user", {"api_key": argument_key}, headers={"x-api-key": "not-a-real-key"})
        assert "API key is not valid" in self._error_text(result)

    def test_bearer_token_without_oidc(self) -> None:
        # Like the REST API, a Bearer token is an OIDC access token, never a Galaxy API key.
        error = self._error_text(self._call_tool("get_user", {}, headers={"Authorization": "Bearer not-a-real-token"}))
        assert "Invalid access token" in error
        assert "x-api-key header" in error

    def test_invalid_bearer_token_with_valid_argument(self) -> None:
        _, argument_key = self._setup_user_get_key("mcp-argument-behind-bearer@bx.psu.edu")
        result = self._call_tool(
            "get_user", {"api_key": argument_key}, headers={"Authorization": "Bearer not-a-real-token"}
        )
        assert "Invalid access token" in self._error_text(result)

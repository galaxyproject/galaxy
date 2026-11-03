"""Helpers for calling Galaxy's MCP server over Streamable HTTP in tests."""

import json

import requests


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

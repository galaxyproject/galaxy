"""
Helper utilities for MCP server to interact with Galaxy REST API.

This module provides utilities for the MCP server to make authenticated
requests to Galaxy's internal REST API endpoints.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class GalaxyAPIClient:
    """Client for making internal API calls to Galaxy."""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the Galaxy API client.

        Args:
            base_url: Base URL of the Galaxy instance (e.g., 'http://localhost:8080')
            api_key: Galaxy API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    def _make_request(
        self, method: str, endpoint: str, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Make an HTTP request to the Galaxy API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., '/api/tools')
            params: Query parameters
            json: JSON body for POST/PUT requests

        Returns:
            Response data as dictionary

        Raises:
            ValueError: If the API request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client() as client:
                response = client.request(
                    method=method, url=url, headers=self.headers, params=params, json=json, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = error_data.get("err_msg", str(error_data))
            except Exception:
                error_detail = e.response.text

            raise ValueError(
                f"Galaxy API request failed: {e.response.status_code} - {error_detail} (endpoint: {endpoint})"
            ) from e
        except httpx.RequestError as e:
            raise ValueError(f"Failed to connect to Galaxy API at {url}: {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Unexpected error calling Galaxy API: {str(e)}") from e

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to the Galaxy API."""
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a POST request to the Galaxy API."""
        return self._make_request("POST", endpoint, json=json)

    def put(self, endpoint: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a PUT request to the Galaxy API."""
        return self._make_request("PUT", endpoint, json=json)

    def delete(self, endpoint: str) -> dict[str, Any]:
        """Make a DELETE request to the Galaxy API."""
        return self._make_request("DELETE", endpoint)

    # Convenience methods for common Galaxy API operations

    def get_config(self) -> dict[str, Any]:
        """Get Galaxy server configuration."""
        return self.get("/api/configuration")

    def get_current_user(self) -> dict[str, Any]:
        """Get current user information."""
        return self.get("/api/users/current")

    def get_version(self) -> dict[str, Any]:
        """Get Galaxy version information."""
        return self.get("/api/version")

    def search_tools(self, query: str | None = None) -> list[dict[str, Any]]:
        """Search for tools by name or query."""
        params = {}
        if query:
            params["q"] = query
        return self.get("/api/tools", params=params)

    def get_tool_details(self, tool_id: str, io_details: bool = False) -> dict[str, Any]:
        """Get detailed information about a specific tool."""
        endpoint = f"/api/tools/{tool_id}"
        params = {"io_details": str(io_details).lower()}
        return self.get(endpoint, params=params)

    def list_histories(
        self, limit: int | None = None, offset: int = 0, name: str | None = None
    ) -> list[dict[str, Any]]:
        """List user histories with optional pagination."""
        params: dict[str, Any] = {"offset": offset}
        if limit is not None:
            params["limit"] = limit
        if name is not None:
            params["name"] = name
        return self.get("/api/histories", params=params)

    def get_history_details(self, history_id: str) -> dict[str, Any]:
        """Get details for a specific history."""
        return self.get(f"/api/histories/{history_id}")

    def create_history(self, name: str) -> dict[str, Any]:
        """Create a new history."""
        return self.post("/api/histories", json={"name": name})

    def run_tool(self, history_id: str, tool_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Run a tool in Galaxy.

        Args:
            history_id: ID of the history to run the tool in
            tool_id: ID of the tool to run
            inputs: Tool input parameters

        Returns:
            Job execution information
        """
        payload = {"history_id": history_id, "tool_id": tool_id, "inputs": inputs}
        return self.post("/api/tools", json=payload)

"""
Model Context Protocol (MCP) server integration for Galaxy.

This module provides MCP tools that allow AI assistants to interact
with Galaxy programmatically. Tools are thin wrappers around the
AgentOperationsManager which provides the actual functionality.
"""

import logging
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def get_mcp_app(gx_app):
    """
    Create and configure the MCP server application.

    Args:
        gx_app: Galaxy application instance

    Returns:
        FastAPI application with MCP endpoints
    """
    # Create MCP server instance
    mcp = FastMCP("Galaxy", dependencies=["httpx>=0.27.0"])

    # Get Galaxy base URL from config
    # Use galaxy_infrastructure_url if available, otherwise construct from host/port
    if hasattr(gx_app.config, "galaxy_infrastructure_url") and gx_app.config.galaxy_infrastructure_url:
        base_url = gx_app.config.galaxy_infrastructure_url.rstrip("/")
    else:
        # Fallback to localhost for internal API calls
        base_url = "http://localhost:8080"

    logger.info(f"MCP server configured to use Galaxy API at: {base_url}")

    # Helper function to create AgentOperationsManager
    def get_operations_manager(api_key: str):
        """
        Create AgentOperationsManager for external mode.

        Args:
            api_key: Galaxy API key for authentication
        """
        if not api_key:
            raise ValueError(
                "API key required. You can create an API key in Galaxy "
                "under User -> Preferences -> Manage API Key."
            )

        from galaxy.managers.agent_operations import AgentOperationsManager

        return AgentOperationsManager(api_key=api_key, base_url=base_url)

    # Define MCP tools
    # All tools are thin wrappers around AgentOperationsManager

    @mcp.tool()
    def connect(api_key: str) -> dict[str, Any]:
        """
        Verify connection to Galaxy and get server information.

        This tool checks that the API key is valid and returns basic
        information about the Galaxy server and current user.

        Args:
            api_key: Galaxy API key for authentication

        Returns:
            Server configuration, version info, and current user details
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.connect()
        except Exception as e:
            logger.error(f"Failed to connect to Galaxy: {str(e)}")
            raise ValueError(f"Failed to connect to Galaxy: {str(e)}") from e

    @mcp.tool()
    def search_tools(query: str, api_key: str) -> dict[str, Any]:
        """
        Search for Galaxy tools by name or keyword.

        Use this to find available tools in Galaxy. The search matches against
        tool names, IDs, and descriptions.

        Args:
            query: Search query (tool name or keyword to search for)
            api_key: Galaxy API key for authentication

        Returns:
            List of matching tools with their IDs, names, and descriptions
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.search_tools(query)
        except Exception as e:
            logger.error(f"Failed to search tools: {str(e)}")
            raise ValueError(f"Failed to search tools: {str(e)}") from e

    @mcp.tool()
    def get_tool_details(tool_id: str, api_key: str, io_details: bool = False) -> dict[str, Any]:
        """
        Get detailed information about a specific Galaxy tool.

        Use this to learn about a tool's parameters, inputs, outputs,
        and how to use it. Set io_details=true to get full input/output
        specifications needed for running the tool.

        Args:
            tool_id: Galaxy tool ID (e.g., 'Cut1' or 'toolshed.g2.bx.psu.edu/repos/...')
            api_key: Galaxy API key for authentication
            io_details: Include detailed input/output specifications (default: false)

        Returns:
            Tool details including parameters, inputs, outputs, and documentation
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_tool_details(tool_id, io_details)
        except Exception as e:
            logger.error(f"Failed to get tool details for {tool_id}: {str(e)}")
            raise ValueError(f"Failed to get tool details for '{tool_id}': {str(e)}") from e

    @mcp.tool()
    def list_histories(api_key: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """
        List the current user's Galaxy histories.

        Histories are containers for datasets and analysis results in Galaxy.
        Use this to find which history to use for running tools.

        Args:
            api_key: Galaxy API key for authentication
            limit: Maximum number of histories to return (default: 50)
            offset: Number of histories to skip for pagination (default: 0)

        Returns:
            List of histories with their IDs, names, and states
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.list_histories(limit, offset)
        except Exception as e:
            logger.error(f"Failed to list histories: {str(e)}")
            raise ValueError(f"Failed to list histories: {str(e)}") from e

    @mcp.tool()
    def run_tool(history_id: str, tool_id: str, inputs: dict[str, Any], api_key: str) -> dict[str, Any]:
        """
        Execute a Galaxy tool.

        Use get_tool_details() with io_details=true first to learn what
        inputs the tool requires and how to format them.

        Args:
            history_id: ID of the history to run the tool in (from list_histories)
            tool_id: ID of the tool to run (from search_tools or get_tool_details)
            inputs: Dictionary of tool input parameters matching the tool's input schema
            api_key: Galaxy API key for authentication

        Returns:
            Job execution information including job IDs and output dataset IDs
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.run_tool(history_id, tool_id, inputs)
        except Exception as e:
            logger.error(f"Failed to run tool {tool_id}: {str(e)}")
            raise ValueError(f"Failed to run tool '{tool_id}' in history '{history_id}': {str(e)}") from e

    # Create the HTTP app for mounting
    # The path="/mcp" parameter here is just for SSE endpoint naming
    # The actual mount point is determined by fast_app.py
    mcp_app = mcp.sse_app()

    logger.info("MCP server initialized with 5 core tools")
    return mcp_app

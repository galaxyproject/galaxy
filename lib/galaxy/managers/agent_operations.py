"""
Manager for AI agent operations on Galaxy.

This manager provides a unified interface for AI agents (both external via MCP
and internal via pydantic-ai) to interact with Galaxy. It supports two modes:

1. Internal mode: Uses SessionRequestContext and Galaxy managers directly (faster)
2. External mode: Uses API key and makes REST API calls (for external clients)
"""

import logging
from typing import Any, Optional

from galaxy.managers.context import ProvidesUserContext
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class AgentOperationsManager:
    """
    Manager for AI agent operations on Galaxy.

    Supports both internal (SessionRequestContext) and external (API key) access modes.
    """

    def __init__(
        self,
        app: Optional[MinimalManagerApp] = None,
        trans: Optional[ProvidesUserContext] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the agent operations manager.

        Internal mode: Provide app and trans (uses Galaxy managers directly)
        External mode: Provide api_key and base_url (uses REST API)

        Args:
            app: Galaxy application instance (for internal mode)
            trans: User session/request context (for internal mode)
            api_key: Galaxy API key (for external mode)
            base_url: Galaxy base URL (for external mode)
        """
        self.app = app
        self.trans = trans
        self._api_key = api_key
        self._base_url = base_url
        self._api_client = None

        # Validate we have one mode or the other
        has_internal = app is not None and trans is not None
        has_external = api_key is not None and base_url is not None

        if not (has_internal or has_external):
            raise ValueError(
                "AgentOperationsManager requires either (app + trans) for internal mode "
                "or (api_key + base_url) for external mode"
            )

        self._mode = "internal" if has_internal else "external"
        log.debug(f"AgentOperationsManager initialized in {self._mode} mode")

    @property
    def api_client(self):
        """Lazy-load API client for external mode."""
        if self._mode == "internal":
            raise RuntimeError("API client not available in internal mode")

        if self._api_client is None:
            # Import here to avoid circular dependency
            from galaxy.webapps.galaxy.api.mcp_helpers import GalaxyAPIClient

            self._api_client = GalaxyAPIClient(base_url=self._base_url, api_key=self._api_key)

        return self._api_client

    def connect(self) -> dict[str, Any]:
        """
        Verify connection to Galaxy and get server information.

        Returns:
            Server configuration, version info, and current user details
        """
        if self._mode == "internal":
            # Use direct access to app and trans
            config = self.app.config
            user = self.trans.user

            if not user:
                raise ValueError("User must be authenticated")

            return {
                "connected": True,
                "server": {
                    "version": config.version_major,
                    "brand": getattr(config, "brand", "Galaxy"),
                    "url": getattr(config, "galaxy_infrastructure_url", "http://localhost:8080"),
                },
                "user": {
                    "id": self.trans.security.encode_id(user.id),
                    "email": user.email,
                    "username": user.username,
                },
            }
        else:
            # Use REST API
            client = self.api_client
            config = client.get_config()
            version = client.get_version()
            user = client.get_current_user()

            return {
                "connected": True,
                "server": {
                    "version": version.get("version_major"),
                    "brand": config.get("brand", "Galaxy"),
                    "url": self._base_url,
                },
                "user": {
                    "id": user.get("id"),
                    "email": user.get("email"),
                    "username": user.get("username"),
                },
            }

    def search_tools(self, query: str) -> dict[str, Any]:
        """
        Search for Galaxy tools by name or keyword.

        Args:
            query: Search query (tool name or keyword)

        Returns:
            List of matching tools with their IDs, names, and descriptions
        """
        if self._mode == "internal":
            # Use toolbox directly
            toolbox = self.app.toolbox

            # Search tools by name/id
            tools = []
            for tool_id, tool in toolbox.tools():
                if tool is None:
                    continue

                # Match against id, name, or description
                matches = (
                    query.lower() in tool_id.lower()
                    or (tool.name and query.lower() in tool.name.lower())
                    or (tool.description and query.lower() in tool.description.lower())
                )

                if matches:
                    tools.append(
                        {
                            "id": tool_id,
                            "name": tool.name,
                            "description": tool.description or "",
                            "version": tool.version,
                        }
                    )

            return {"query": query, "tools": tools, "count": len(tools)}
        else:
            # Use REST API
            client = self.api_client
            tools = client.search_tools(query=query)

            # Format the response
            formatted_tools = []
            for tool in tools:
                formatted_tools.append(
                    {
                        "id": tool.get("id"),
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "version": tool.get("version"),
                    }
                )

            return {"query": query, "tools": formatted_tools, "count": len(formatted_tools)}

    def get_tool_details(self, tool_id: str, io_details: bool = False) -> dict[str, Any]:
        """
        Get detailed information about a specific Galaxy tool.

        Args:
            tool_id: Galaxy tool ID
            io_details: Include detailed input/output specifications

        Returns:
            Tool details including parameters, inputs, outputs, and documentation
        """
        if self._mode == "internal":
            # Use toolbox directly
            toolbox = self.app.toolbox
            tool = toolbox.get_tool(tool_id)

            if tool is None:
                raise ValueError(f"Tool '{tool_id}' not found")

            # Build tool info dict
            tool_info = {
                "id": tool.id,
                "name": tool.name,
                "version": tool.version,
                "description": tool.description or "",
                "help": tool.help or "",
            }

            if io_details:
                # Add input/output details
                tool_info["inputs"] = []
                for input_param in tool.inputs.values():
                    tool_info["inputs"].append(
                        {
                            "name": input_param.name,
                            "type": input_param.type,
                            "label": getattr(input_param, "label", input_param.name),
                            "help": getattr(input_param, "help", ""),
                            "optional": getattr(input_param, "optional", False),
                        }
                    )

                # Add outputs
                tool_info["outputs"] = []
                for output in tool.outputs.values():
                    tool_info["outputs"].append(
                        {
                            "name": output.name,
                            "format": getattr(output, "format", "data"),
                            "label": getattr(output, "label", output.name),
                        }
                    )

            return tool_info
        else:
            # Use REST API
            client = self.api_client
            return client.get_tool_details(tool_id=tool_id, io_details=io_details)

    def list_histories(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """
        List the current user's Galaxy histories.

        Args:
            limit: Maximum number of histories to return
            offset: Number of histories to skip for pagination

        Returns:
            List of histories with their IDs, names, and states
        """
        if self._mode == "internal":
            # Use history manager
            from galaxy.managers.histories import HistoryManager

            history_manager = HistoryManager(self.app)

            # Get user's histories
            histories = history_manager.list_for_user(self.trans, limit=limit, offset=offset)

            # Format the response
            formatted_histories = []
            for hist in histories:
                formatted_histories.append(
                    {
                        "id": self.trans.security.encode_id(hist.id),
                        "name": hist.name,
                        "state": hist.state,
                        "deleted": hist.deleted,
                        "published": hist.published,
                        "update_time": hist.update_time.isoformat() if hist.update_time else None,
                    }
                )

            return {
                "histories": formatted_histories,
                "count": len(formatted_histories),
                "pagination": {"limit": limit, "offset": offset},
            }
        else:
            # Use REST API
            client = self.api_client
            histories = client.list_histories(limit=limit, offset=offset)

            # Format the response
            formatted_histories = []
            for hist in histories:
                formatted_histories.append(
                    {
                        "id": hist.get("id"),
                        "name": hist.get("name"),
                        "state": hist.get("state"),
                        "deleted": hist.get("deleted", False),
                        "published": hist.get("published", False),
                        "update_time": hist.get("update_time"),
                    }
                )

            return {
                "histories": formatted_histories,
                "count": len(formatted_histories),
                "pagination": {"limit": limit, "offset": offset},
            }

    def run_tool(self, history_id: str, tool_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a Galaxy tool.

        Args:
            history_id: ID of the history to run the tool in
            tool_id: ID of the tool to run
            inputs: Dictionary of tool input parameters

        Returns:
            Job execution information including job IDs and output dataset IDs
        """
        if self._mode == "internal":
            # Use tools manager to execute the tool
            from galaxy.managers.tools import ToolsManager

            tools_manager = ToolsManager(self.app)

            # Decode history ID
            decoded_history_id = self.trans.security.decode_id(history_id)

            # Build tool execution payload
            payload = {"history_id": history_id, "tool_id": tool_id, "inputs": inputs}

            # Execute the tool
            result = tools_manager.create_tool_execution(self.trans, payload)

            return result
        else:
            # Use REST API
            client = self.api_client
            return client.run_tool(history_id=history_id, tool_id=tool_id, inputs=inputs)

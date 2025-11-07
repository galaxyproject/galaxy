"""
Manager for AI agent operations on Galaxy.

This manager provides a unified interface for AI agents (both external via MCP
and internal via pydantic-ai) to interact with Galaxy using Galaxy managers directly.

All agents (external MCP clients and internal pydantic-ai) use the same code path
through this manager, ensuring consistent behavior and avoiding HTTP overhead.
"""

import logging
from typing import Any

from galaxy.managers.context import ProvidesUserContext
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class AgentOperationsManager:
    """
    Manager for AI agent operations on Galaxy.

    Provides a unified interface for AI agents to interact with Galaxy through
    direct manager calls. Both external (MCP) and internal (pydantic-ai) agents
    use the same implementation.
    """

    def __init__(self, app: MinimalManagerApp, trans: ProvidesUserContext):
        """
        Initialize the agent operations manager.

        Args:
            app: Galaxy application instance
            trans: User session/request context (WorkRequestContext or SessionRequestContext)
        """
        self.app = app
        self.trans = trans
        log.debug("AgentOperationsManager initialized")

    def connect(self) -> dict[str, Any]:
        """
        Verify connection to Galaxy and get server information.

        Returns:
            Server configuration, version info, and current user details
        """
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

    def search_tools(self, query: str) -> dict[str, Any]:
        """
        Search for Galaxy tools by name or keyword.

        Args:
            query: Search query (tool name or keyword)

        Returns:
            List of matching tools with their IDs, names, and descriptions
        """
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

    def get_tool_details(self, tool_id: str, io_details: bool = False) -> dict[str, Any]:
        """
        Get detailed information about a specific Galaxy tool.

        Args:
            tool_id: Galaxy tool ID
            io_details: Include detailed input/output specifications

        Returns:
            Tool details including parameters, inputs, outputs, and documentation
        """
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
            "help": str(tool.help) if tool.help else "",
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

    def list_histories(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """
        List the current user's Galaxy histories.

        Args:
            limit: Maximum number of histories to return
            offset: Number of histories to skip for pagination

        Returns:
            List of histories with their IDs, names, and states
        """
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

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """
        Get the status and details of a Galaxy job.

        Args:
            job_id: ID of the job to check

        Returns:
            Job details including state, tool info, and timestamps
        """
        # Use jobs manager to get job details
        from galaxy.managers.jobs import JobManager

        job_manager = JobManager(self.app)

        # Decode job ID
        decoded_job_id = self.trans.security.decode_id(job_id)

        # Get job details
        job = job_manager.by_id(decoded_job_id)

        # Build job info dict
        job_info = {
            "id": job_id,
            "state": job.state,
            "tool_id": job.tool_id,
            "create_time": job.create_time.isoformat() if job.create_time else None,
            "update_time": job.update_time.isoformat() if job.update_time else None,
            "exit_code": job.exit_code,
            "history_id": self.trans.security.encode_id(job.history_id) if job.history_id else None,
        }

        return {"job": job_info, "job_id": job_id}

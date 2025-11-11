"""
Manager for AI agent operations on Galaxy.

This manager provides a unified interface for AI agents (both external via MCP
and internal via pydantic-ai) to interact with Galaxy using the Galaxy API service layer.

All agents (external MCP clients and internal pydantic-ai) use the same code path
through this manager, which delegates to the service layer to ensure proper validation,
rate limiting, pagination, and other API safeguards.
"""

import logging
from typing import Any

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
)
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class AgentOperationsManager:
    """
    Manager for AI agent operations on Galaxy.

    Provides a unified interface for AI agents to interact with Galaxy through
    the service layer. Both external (MCP) and internal (pydantic-ai) agents
    use the same implementation, which delegates to Galaxy services for proper
    validation, permission checks, and API safeguards.
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

        # Initialize services - these provide the proper API layer with validation,
        # rate limiting, pagination, etc.
        self._tools_service = None
        self._histories_service = None
        self._jobs_service = None

        log.debug("AgentOperationsManager initialized")

    @property
    def tools_service(self):
        """Lazy-load ToolsService."""
        if self._tools_service is None:
            from galaxy.managers.histories import HistoryManager
            from galaxy.tools.search import ToolBoxSearch
            from galaxy.webapps.galaxy.services.tools import ToolsService

            self._tools_service = ToolsService(
                config=self.app.config,
                toolbox_search=ToolBoxSearch(self.app.toolbox),
                security=self.trans.security,
                history_manager=HistoryManager(self.app),
            )
        return self._tools_service

    @property
    def histories_service(self):
        """Lazy-load HistoriesService."""
        if self._histories_service is None:
            from galaxy.managers.citations import CitationsManager
            from galaxy.managers.histories import (
                HistoryDeserializer,
                HistoryExportManager,
                HistoryFilters,
                HistoryManager,
                HistorySerializer,
            )
            from galaxy.managers.users import UserManager
            from galaxy.short_term_storage import ShortTermStorageAllocator
            from galaxy.webapps.galaxy.services.histories import HistoriesService
            from galaxy.webapps.galaxy.services.notifications import NotificationService

            history_manager = HistoryManager(self.app)
            self._histories_service = HistoriesService(
                security=self.trans.security,
                manager=history_manager,
                user_manager=UserManager(self.app),
                serializer=HistorySerializer(self.app),
                deserializer=HistoryDeserializer(self.app),
                citations_manager=CitationsManager(self.app),
                history_export_manager=HistoryExportManager(self.app),
                filters=HistoryFilters(self.app),
                short_term_storage_allocator=ShortTermStorageAllocator(self.app.config),
                notification_service=NotificationService(self.trans.sa_session, self.trans.security),
            )
        return self._histories_service

    @property
    def jobs_service(self):
        """Lazy-load JobsService."""
        if self._jobs_service is None:
            from galaxy.managers.hdas import HDAManager
            from galaxy.managers.histories import HistoryManager
            from galaxy.managers.jobs import (
                JobManager,
                JobSearch,
            )
            from galaxy.webapps.galaxy.services.jobs import JobsService

            self._jobs_service = JobsService(
                security=self.trans.security,
                job_manager=JobManager(self.app),
                job_search=JobSearch(self.app),
                hda_manager=HDAManager(self.app),
                history_manager=HistoryManager(self.app),
            )
        return self._jobs_service

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
        # Use the service layer's search which handles boosts and config properly
        tool_ids = self.tools_service._search(query, view=None)

        # Get tool details for each result
        tools = []
        for tool_id in tool_ids:
            try:
                tool = self.tools_service._get_tool(self.trans, tool_id, user=self.trans.user)
                if tool:
                    tools.append(
                        {
                            "id": tool.id,
                            "name": tool.name,
                            "description": tool.description or "",
                            "version": tool.version,
                        }
                    )
            except Exception as e:
                # Skip tools that fail to load or user doesn't have access to
                log.debug(f"Skipping tool {tool_id}: {str(e)}")
                continue

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
        # Use service layer to get tool with proper permission checks
        tool = self.tools_service._get_tool(self.trans, tool_id, user=self.trans.user)

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
        # Use the service layer for proper pagination and filtering
        serialization_params = SerializationParams(view="summary")
        filter_params = FilterQueryParams(limit=limit, offset=offset)

        # Get histories using the service layer
        histories = self.histories_service.index(
            trans=self.trans,
            serialization_params=serialization_params,
            filter_query_params=filter_params,
            deleted_only=False,
            all_histories=False,
        )

        return {
            "histories": histories,
            "count": len(histories),
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
        # Build tool execution payload matching the API format
        payload = {
            "history_id": history_id,
            "tool_id": tool_id,
            "inputs": inputs,
        }

        # Execute the tool using the service layer
        # This ensures proper validation, permission checks, and all API safeguards
        result = self.tools_service._create(self.trans, payload)

        return result

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """
        Get the status and details of a Galaxy job.

        Args:
            job_id: ID of the job to check

        Returns:
            Job details including state, tool info, and timestamps
        """
        # Decode job ID
        decoded_job_id = self.trans.security.decode_id(job_id)

        # Get job details using the service layer
        # This ensures proper permission checks and access control
        job_details = self.jobs_service.show(
            trans=self.trans,
            id=decoded_job_id,
            full=False,
        )

        return {"job": job_details, "job_id": job_id}

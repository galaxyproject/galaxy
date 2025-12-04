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
        self._datasets_service = None

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

    @property
    def datasets_service(self):
        """Lazy-load DatasetsService."""
        if self._datasets_service is None:
            from galaxy.managers.datasets import DatasetManager
            from galaxy.managers.hdas import (
                HDAManager,
                HDASerializer,
            )
            from galaxy.managers.hdcas import HDCASerializer
            from galaxy.managers.histories import HistoryManager
            from galaxy.managers.history_contents import (
                HistoryContentsFilters,
                HistoryContentsManager,
            )
            from galaxy.managers.lddas import LDDAManager
            from galaxy.visualization.data_providers.registry import DataProviderRegistry
            from galaxy.webapps.galaxy.services.datasets import DatasetsService

            self._datasets_service = DatasetsService(
                security=self.trans.security,
                history_manager=HistoryManager(self.app),
                hda_manager=HDAManager(self.app),
                hda_serializer=HDASerializer(self.app),
                hdca_serializer=HDCASerializer(self.app),
                ldda_manager=LDDAManager(self.app),
                history_contents_manager=HistoryContentsManager(self.app),
                history_contents_filters=HistoryContentsFilters(self.app),
                data_provider_registry=DataProviderRegistry(),
                dataset_manager=DatasetManager(self.app),
            )
        return self._datasets_service

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

    def create_history(self, name: str) -> dict[str, Any]:
        """
        Create a new Galaxy history.

        Args:
            name: Name for the new history

        Returns:
            Created history details including ID, name, and state
        """
        from galaxy.schema.schema import CreateHistoryPayload

        payload = CreateHistoryPayload(name=name)
        serialization_params = SerializationParams(view="summary")

        history = self.histories_service.create(
            trans=self.trans,
            payload=payload,
            serialization_params=serialization_params,
        )

        return history

    def get_history_details(self, history_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific history.

        This returns history metadata without loading all datasets.
        Use get_history_contents() to get the actual datasets.

        Args:
            history_id: Galaxy history ID (encoded)

        Returns:
            History details including metadata and summary statistics
        """
        decoded_history_id = self.trans.security.decode_id(history_id)
        serialization_params = SerializationParams(view="detailed")

        history = self.histories_service.show(
            trans=self.trans,
            serialization_params=serialization_params,
            history_id=decoded_history_id,
        )

        return {"history": history, "history_id": history_id}

    def get_history_contents(
        self,
        history_id: str,
        limit: int = 100,
        offset: int = 0,
        order: str = "hid-asc",
    ) -> dict[str, Any]:
        """
        Get paginated contents (datasets) from a specific history.

        Args:
            history_id: Galaxy history ID (encoded)
            limit: Maximum number of items to return (default: 100)
            offset: Number of items to skip for pagination (default: 0)
            order: Sort order (e.g., 'hid-asc', 'hid-dsc', 'create_time-dsc')

        Returns:
            List of datasets/collections in the history with pagination info
        """
        decoded_history_id = self.trans.security.decode_id(history_id)
        serialization_params = SerializationParams(view="summary")
        filter_params = FilterQueryParams(limit=limit, offset=offset, order=order)

        contents, total_count = self.datasets_service.index(
            trans=self.trans,
            history_id=decoded_history_id,
            serialization_params=serialization_params,
            filter_query_params=filter_params,
        )

        # Calculate pagination metadata
        has_next = (offset + limit) < total_count
        has_previous = offset > 0
        current_page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = ((total_count - 1) // limit) + 1 if limit > 0 and total_count > 0 else 1

        return {
            "history_id": history_id,
            "contents": contents,
            "pagination": {
                "total_items": total_count,
                "returned_items": len(contents),
                "limit": limit,
                "offset": offset,
                "current_page": current_page,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
            },
        }

    def get_dataset_details(self, dataset_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific dataset.

        Args:
            dataset_id: Galaxy dataset ID (encoded)

        Returns:
            Dataset details including metadata, state, and file information
        """
        from galaxy.schema.schema import DatasetSourceType

        decoded_dataset_id = self.trans.security.decode_id(dataset_id)
        serialization_params = SerializationParams(view="detailed")

        dataset = self.datasets_service.show(
            trans=self.trans,
            dataset_id=decoded_dataset_id,
            hda_ldda=DatasetSourceType.hda,
            serialization_params=serialization_params,
        )

        return {"dataset": dataset, "dataset_id": dataset_id}

    def upload_file_from_url(
        self,
        history_id: str,
        url: str,
        file_type: str = "auto",
        dbkey: str = "?",
        file_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload a file from a URL to Galaxy.

        Args:
            history_id: ID of the history to upload to
            url: URL of the file to upload
            file_type: Galaxy file format (default: 'auto' for auto-detection)
            dbkey: Database key/genome build (default: '?')
            file_name: Optional name for the uploaded file

        Returns:
            Job execution information including job ID and output dataset IDs
        """
        # Build the upload tool payload
        # The upload tool (upload1) uses files_0|url_paste for URL uploads
        inputs = {
            "files_0|url_paste": url,
            "files_0|type": "upload_dataset",
            "files_0|auto_decompress": True,
            "file_type": file_type,
            "dbkey": dbkey,
        }

        if file_name:
            inputs["files_0|name"] = file_name

        # Run the upload tool
        payload = {
            "history_id": history_id,
            "tool_id": "upload1",
            "inputs": inputs,
        }

        result = self.tools_service._create(self.trans, payload)

        return result

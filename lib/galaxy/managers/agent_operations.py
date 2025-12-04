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
        self._workflows_service = None
        self._invocations_service = None

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

    @property
    def workflows_service(self):
        """Lazy-load WorkflowsService."""
        if self._workflows_service is None:
            from galaxy.managers.workflows import (
                WorkflowContentsManager,
                WorkflowsManager,
            )
            from galaxy.model.store import SessionlessContext
            from galaxy.webapps.galaxy.services.notifications import NotificationService
            from galaxy.webapps.galaxy.services.workflows import WorkflowsService
            from galaxy.workflow.modules import WorkflowModuleFactory

            workflow_contents_manager = WorkflowContentsManager(
                self.app,
                WorkflowModuleFactory(self.app.toolbox),
                SessionlessContext(),
            )
            workflows_manager = WorkflowsManager(self.app)
            self._workflows_service = WorkflowsService(
                workflows_manager=workflows_manager,
                workflow_contents_manager=workflow_contents_manager,
                serializer=workflows_manager.get_serializer(),
                tool_shed_registry=self.app.tool_shed_registry,
                notification_service=NotificationService(self.trans.sa_session, self.trans.security),
            )
        return self._workflows_service

    @property
    def invocations_service(self):
        """Lazy-load InvocationsService."""
        if self._invocations_service is None:
            from galaxy.managers.histories import HistoryManager
            from galaxy.managers.workflows import WorkflowsManager
            from galaxy.short_term_storage import ShortTermStorageAllocator
            from galaxy.webapps.galaxy.services.invocations import InvocationsService

            self._invocations_service = InvocationsService(
                security=self.trans.security,
                histories_manager=HistoryManager(self.app),
                workflows_manager=WorkflowsManager(self.app),
                short_term_storage_allocator=ShortTermStorageAllocator(self.app.config),
            )
        return self._invocations_service

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

    def list_workflows(
        self,
        limit: int = 50,
        offset: int = 0,
        show_published: bool = False,
        show_shared: bool = True,
        search: str | None = None,
    ) -> dict[str, Any]:
        """
        List user's workflows.

        Args:
            limit: Maximum number of workflows to return (default: 50)
            offset: Number of workflows to skip for pagination (default: 0)
            show_published: Include published workflows (default: False)
            show_shared: Include workflows shared with user (default: True)
            search: Optional search term to filter workflows

        Returns:
            List of workflows with their IDs, names, and basic metadata
        """
        from galaxy.webapps.galaxy.services.workflows import WorkflowIndexPayload

        payload = WorkflowIndexPayload(
            limit=limit,
            offset=offset,
            show_published=show_published,
            show_shared=show_shared,
            search=search,
        )

        workflows, total_count = self.workflows_service.index(
            trans=self.trans,
            payload=payload,
            include_total_count=True,
        )

        return {
            "workflows": workflows,
            "count": len(workflows),
            "total_count": total_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
            },
        }

    def get_workflow_details(self, workflow_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific workflow.

        Args:
            workflow_id: Galaxy workflow ID (encoded)

        Returns:
            Workflow details including steps, inputs, and outputs
        """
        decoded_workflow_id = self.trans.security.decode_id(workflow_id)

        workflow = self.workflows_service.show_workflow(
            trans=self.trans,
            workflow_id=decoded_workflow_id,
            instance=False,
            legacy=False,
            version=None,
        )

        return {"workflow": workflow, "workflow_id": workflow_id}

    def invoke_workflow(
        self,
        workflow_id: str,
        history_id: str,
        inputs: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Invoke (run) a workflow.

        Args:
            workflow_id: Galaxy workflow ID (encoded)
            history_id: History ID to run the workflow in
            inputs: Dictionary mapping workflow input labels/indices to dataset IDs
            parameters: Dictionary mapping step IDs to parameter values

        Returns:
            Workflow invocation details including invocation ID
        """
        from galaxy.schema.workflows import InvokeWorkflowPayload

        decoded_workflow_id = self.trans.security.decode_id(workflow_id)

        payload = InvokeWorkflowPayload(
            history_id=history_id,
            inputs=inputs or {},
            parameters=parameters or {},
        )

        result = self.workflows_service.invoke_workflow(
            trans=self.trans,
            workflow_id=decoded_workflow_id,
            payload=payload,
        )

        return result

    def get_invocations(
        self,
        workflow_id: str | None = None,
        history_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List workflow invocations.

        Args:
            workflow_id: Optional workflow ID to filter by
            history_id: Optional history ID to filter by
            limit: Maximum number of invocations to return (default: 50)
            offset: Number of invocations to skip (default: 0)

        Returns:
            List of workflow invocations with their status
        """
        from galaxy.schema.invocation import (
            InvocationIndexPayload,
            InvocationSerializationParams,
        )

        decoded_workflow_id = None
        if workflow_id:
            decoded_workflow_id = self.trans.security.decode_id(workflow_id)

        decoded_history_id = None
        if history_id:
            decoded_history_id = self.trans.security.decode_id(history_id)

        payload = InvocationIndexPayload(
            workflow_id=decoded_workflow_id,
            history_id=decoded_history_id,
            limit=limit,
            offset=offset,
        )
        serialization_params = InvocationSerializationParams(view="collection")

        invocations, total_count = self.invocations_service.index(
            trans=self.trans,
            invocation_payload=payload,
            serialization_params=serialization_params,
        )

        return {
            "invocations": invocations,
            "count": len(invocations),
            "total_count": total_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
            },
        }

    def get_invocation_details(self, invocation_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific workflow invocation.

        Args:
            invocation_id: Workflow invocation ID (encoded)

        Returns:
            Invocation details including state, steps, and outputs
        """
        from galaxy.schema.invocation import InvocationSerializationParams

        decoded_invocation_id = self.trans.security.decode_id(invocation_id)
        serialization_params = InvocationSerializationParams(view="element")

        invocation = self.invocations_service.show(
            trans=self.trans,
            invocation_id=decoded_invocation_id,
            serialization_params=serialization_params,
        )

        return {"invocation": invocation, "invocation_id": invocation_id}

    def cancel_workflow_invocation(self, invocation_id: str) -> dict[str, Any]:
        """
        Cancel a running workflow invocation.

        Args:
            invocation_id: Workflow invocation ID (encoded)

        Returns:
            Updated invocation details with cancelled state
        """
        from galaxy.schema.invocation import InvocationSerializationParams

        decoded_invocation_id = self.trans.security.decode_id(invocation_id)
        serialization_params = InvocationSerializationParams(view="element")

        invocation = self.invocations_service.cancel(
            trans=self.trans,
            invocation_id=decoded_invocation_id,
            serialization_params=serialization_params,
        )

        return {"invocation": invocation, "invocation_id": invocation_id, "cancelled": True}

    def get_tool_panel(self, view: str | None = None) -> dict[str, Any]:
        """
        Get the tool panel (toolbox) structure.

        Args:
            view: Optional panel view name (default: use server default)

        Returns:
            Tool panel hierarchy with sections and tools
        """
        if view is None:
            view = self.app.toolbox._default_panel_view(self.trans)

        tool_panel = self.app.toolbox.to_panel_view(self.trans, view=view)

        return {"tool_panel": tool_panel, "view": view}

    def get_tool_run_examples(self, tool_id: str) -> dict[str, Any]:
        """
        Get test cases/examples for a tool.

        These show how the tool should be run with real inputs.

        Args:
            tool_id: Galaxy tool ID

        Returns:
            Test cases with inputs, outputs, and assertions
        """
        tool = self.tools_service._get_tool(self.trans, tool_id, user=self.trans.user)

        if tool is None:
            raise ValueError(f"Tool '{tool_id}' not found")

        # Get tool tests
        test_cases = []
        if hasattr(tool, "tests") and tool.tests:
            for i, test in enumerate(tool.tests):
                test_case = {
                    "index": i,
                    "inputs": {},
                    "outputs": {},
                }
                # Extract inputs
                if hasattr(test, "inputs"):
                    for name, value in test.inputs.items():
                        test_case["inputs"][name] = str(value) if value is not None else None

                # Extract expected outputs
                if hasattr(test, "outputs"):
                    for output in test.outputs:
                        test_case["outputs"][output.name] = {
                            "file": getattr(output, "file", None),
                            "value": getattr(output, "value", None),
                        }

                test_cases.append(test_case)

        return {
            "tool_id": tool_id,
            "tool_name": tool.name,
            "tool_version": tool.version,
            "test_cases": test_cases,
            "count": len(test_cases),
        }

    def get_tool_citations(self, tool_id: str) -> dict[str, Any]:
        """
        Get citation information for a tool.

        Args:
            tool_id: Galaxy tool ID

        Returns:
            Tool citations including DOIs, BibTeX, etc.
        """
        tool = self.tools_service._get_tool(self.trans, tool_id, user=self.trans.user)

        if tool is None:
            raise ValueError(f"Tool '{tool_id}' not found")

        citations = []
        if hasattr(tool, "citations") and tool.citations:
            for citation in tool.citations:
                citation_info = {
                    "type": getattr(citation, "type", "unknown"),
                }
                if hasattr(citation, "doi"):
                    citation_info["doi"] = citation.doi
                if hasattr(citation, "bibtex"):
                    citation_info["bibtex"] = citation.bibtex
                if hasattr(citation, "url"):
                    citation_info["url"] = citation.url
                citations.append(citation_info)

        return {
            "tool_id": tool_id,
            "tool_name": tool.name,
            "tool_version": tool.version,
            "citations": citations,
            "count": len(citations),
        }

    def search_tools_by_keywords(self, keywords: list[str]) -> dict[str, Any]:
        """
        Search for tools matching multiple keywords.

        Searches tool names, descriptions, and input formats.

        Args:
            keywords: List of keywords to search for

        Returns:
            Matching tools with relevance information
        """
        keywords_lower = [k.lower() for k in keywords]
        matching_tools = []
        seen_tool_ids = set()

        # Search each keyword and aggregate results
        for keyword in keywords:
            tool_ids = self.tools_service._search(keyword, view=None)

            for tool_id in tool_ids:
                if tool_id in seen_tool_ids:
                    continue

                try:
                    tool = self.tools_service._get_tool(self.trans, tool_id, user=self.trans.user)
                    if tool:
                        # Check if any keyword matches name or description
                        name_lower = (tool.name or "").lower()
                        desc_lower = (tool.description or "").lower()

                        matches = []
                        for kw in keywords_lower:
                            if kw in name_lower or kw in desc_lower:
                                matches.append(kw)

                        matching_tools.append(
                            {
                                "id": tool.id,
                                "name": tool.name,
                                "description": tool.description or "",
                                "version": tool.version,
                                "matched_keywords": matches,
                            }
                        )
                        seen_tool_ids.add(tool_id)
                except Exception as e:
                    log.debug(f"Skipping tool {tool_id}: {str(e)}")
                    continue

        # Sort by number of matched keywords (most relevant first)
        matching_tools.sort(key=lambda x: len(x["matched_keywords"]), reverse=True)

        return {
            "keywords": keywords,
            "tools": matching_tools,
            "count": len(matching_tools),
        }

    def _get_iwc_manifest(self) -> list[dict[str, Any]]:
        """
        Fetch the IWC workflow manifest.

        Returns:
            Raw manifest data from IWC
        """
        import httpx

        response = httpx.get("https://iwc.galaxyproject.org/workflow_manifest.json", timeout=30.0)
        response.raise_for_status()
        return response.json()

    def get_iwc_workflows(self) -> dict[str, Any]:
        """
        Get all workflows from the IWC (Intergalactic Workflow Commission).

        IWC hosts community-maintained, production-quality Galaxy workflows.

        Returns:
            List of all IWC workflows with their metadata
        """
        manifest = self._get_iwc_manifest()

        # Collect workflows from all manifest entries
        all_workflows = []
        for entry in manifest:
            if "workflows" in entry:
                for wf in entry["workflows"]:
                    definition = wf.get("definition", {})
                    all_workflows.append(
                        {
                            "trsID": wf.get("trsID"),
                            "name": definition.get("name", ""),
                            "description": definition.get("annotation", ""),
                            "tags": definition.get("tags", []),
                        }
                    )

        return {"workflows": all_workflows, "count": len(all_workflows)}

    def search_iwc_workflows(self, query: str) -> dict[str, Any]:
        """
        Search IWC workflows by name, description, or tags.

        Args:
            query: Search term to match against workflow metadata

        Returns:
            Matching workflows from IWC
        """
        manifest = self._get_iwc_manifest()
        query_lower = query.lower()

        results = []
        for entry in manifest:
            if "workflows" not in entry:
                continue

            for wf in entry["workflows"]:
                definition = wf.get("definition", {})
                name = definition.get("name", "")
                description = definition.get("annotation", "")
                tags = definition.get("tags", [])

                # Check if query matches name, description, or tags
                name_lower = name.lower()
                desc_lower = description.lower()
                tags_lower = [t.lower() for t in tags]

                if (
                    query_lower in name_lower
                    or query_lower in desc_lower
                    or any(query_lower in tag for tag in tags_lower)
                ):
                    results.append(
                        {
                            "trsID": wf.get("trsID"),
                            "name": name,
                            "description": description,
                            "tags": tags,
                        }
                    )

        return {"query": query, "workflows": results, "count": len(results)}

    def import_workflow_from_iwc(self, trs_id: str) -> dict[str, Any]:
        """
        Import a workflow from IWC into Galaxy.

        Args:
            trs_id: TRS ID of the workflow in the IWC manifest

        Returns:
            Imported workflow information
        """
        manifest = self._get_iwc_manifest()

        # Find the workflow by trs_id
        workflow_def = None
        for entry in manifest:
            if "workflows" not in entry:
                continue
            for wf in entry["workflows"]:
                if wf.get("trsID") == trs_id:
                    workflow_def = wf.get("definition")
                    break
            if workflow_def:
                break

        if not workflow_def:
            raise ValueError(
                f"Workflow with trsID '{trs_id}' not found in IWC manifest. "
                "Use search_iwc_workflows() to find valid trsIDs."
            )

        # Import the workflow using the workflows manager
        from galaxy.managers.workflows import WorkflowsManager

        workflows_manager = WorkflowsManager(self.app)
        imported = workflows_manager.import_workflow_dict(self.trans, workflow_def, publish=False)

        return {
            "imported_workflow": {
                "id": self.trans.security.encode_id(imported.id),
                "name": imported.name,
            },
            "trs_id": trs_id,
        }

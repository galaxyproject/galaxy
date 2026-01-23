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

# Fields that contain Galaxy database IDs and should be encoded
ID_FIELDS = {
    "id",
    "history_id",
    "dataset_id",
    "job_id",
    "workflow_id",
    "invocation_id",
    "user_id",
    "hda_id",
    "hdca_id",
    "collection_id",
    "creating_job",
}


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

    def _encode_id(self, value: int) -> str:
        """Encode a single integer ID to a string."""
        return self.trans.security.encode_id(value)

    def _encode_ids_in_response(self, data: Any) -> Any:
        """
        Recursively encode Galaxy database IDs in response data.

        The service layer returns unencoded integer IDs, but agents need
        encoded string IDs to use in subsequent API calls.

        Args:
            data: Response data (dict, list, or scalar)

        Returns:
            Data with integer IDs encoded as strings
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in ID_FIELDS and isinstance(value, int):
                    result[key] = self._encode_id(value)
                else:
                    result[key] = self._encode_ids_in_response(value)
            return result
        elif isinstance(data, list):
            return [self._encode_ids_in_response(item) for item in data]
        else:
            return data

    @property
    def tools_service(self):
        """Get ToolsService from app's DI container."""
        if self._tools_service is None:
            from galaxy.webapps.galaxy.services.tools import ToolsService

            self._tools_service = self.app[ToolsService]
        return self._tools_service

    @property
    def histories_service(self):
        """Get HistoriesService from app's DI container."""
        if self._histories_service is None:
            from galaxy.webapps.galaxy.services.histories import HistoriesService

            self._histories_service = self.app[HistoriesService]
        return self._histories_service

    @property
    def jobs_service(self):
        """Get JobsService from app's DI container."""
        if self._jobs_service is None:
            from galaxy.webapps.galaxy.services.jobs import JobsService

            self._jobs_service = self.app[JobsService]
        return self._jobs_service

    @property
    def datasets_service(self):
        """Get DatasetsService from app's DI container."""
        if self._datasets_service is None:
            from galaxy.webapps.galaxy.services.datasets import DatasetsService

            self._datasets_service = self.app[DatasetsService]
        return self._datasets_service

    @property
    def workflows_service(self):
        """Get WorkflowsService from app's DI container."""
        if self._workflows_service is None:
            from galaxy.webapps.galaxy.services.workflows import WorkflowsService

            self._workflows_service = self.app[WorkflowsService]
        return self._workflows_service

    @property
    def invocations_service(self):
        """Get InvocationsService from app's DI container."""
        if self._invocations_service is None:
            from galaxy.webapps.galaxy.services.invocations import InvocationsService

            self._invocations_service = self.app[InvocationsService]
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
            "help": str(tool.help) if getattr(tool, "help", None) else "",
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

        # Encode IDs in response for agent consumption
        encoded_histories = self._encode_ids_in_response(histories)

        return {
            "histories": encoded_histories,
            "count": len(encoded_histories),
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

        # Encode IDs in response for agent consumption
        return self._encode_ids_in_response(result)

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

        # Encode IDs in response for agent consumption
        return {"job": self._encode_ids_in_response(job_details), "job_id": job_id}

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

        # Encode IDs in response for agent consumption
        return self._encode_ids_in_response(history)

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

        # Encode IDs in response for agent consumption
        return {
            "history": self._encode_ids_in_response(history),
            "history_id": history_id,
        }

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

        # Encode IDs in response for agent consumption
        return {
            "history_id": history_id,
            "contents": self._encode_ids_in_response(contents),
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

        # Encode IDs in response for agent consumption
        return {
            "dataset": self._encode_ids_in_response(dataset),
            "dataset_id": dataset_id,
        }

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

        # Encode IDs in response for agent consumption
        return self._encode_ids_in_response(result)

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

        # Encode IDs in response for agent consumption
        encoded_workflows = self._encode_ids_in_response(workflows)

        return {
            "workflows": encoded_workflows,
            "count": len(encoded_workflows),
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

        # Encode IDs in response for agent consumption
        return {
            "workflow": self._encode_ids_in_response(workflow),
            "workflow_id": workflow_id,
        }

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

        # Encode IDs in response for agent consumption
        return self._encode_ids_in_response(result)

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

        # Encode IDs in response for agent consumption
        encoded_invocations = self._encode_ids_in_response(invocations)

        return {
            "invocations": encoded_invocations,
            "count": len(encoded_invocations),
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

        # Encode IDs in response for agent consumption
        return {
            "invocation": self._encode_ids_in_response(invocation),
            "invocation_id": invocation_id,
        }

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

        # Encode IDs in response for agent consumption
        return {
            "invocation": self._encode_ids_in_response(invocation),
            "invocation_id": invocation_id,
            "cancelled": True,
        }

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

    def list_history_ids(self, limit: int = 100) -> dict[str, Any]:
        """
        Get a simplified list of history IDs and names.

        Args:
            limit: Maximum number of histories to return (default: 100)

        Returns:
            Simplified list of history IDs and names
        """
        serialization_params = SerializationParams(view="summary")
        filter_params = FilterQueryParams(limit=limit, offset=0)

        histories = self.histories_service.index(
            trans=self.trans,
            serialization_params=serialization_params,
            filter_query_params=filter_params,
            deleted_only=False,
            all_histories=False,
        )

        # Return simplified list with just id and name
        # Service returns dicts, encode IDs for agent consumption
        simplified = [
            {
                "id": self._encode_id(h["id"]) if isinstance(h["id"], int) else h["id"],
                "name": h["name"],
            }
            for h in histories
        ]

        return {"histories": simplified, "count": len(simplified)}

    def get_job_details(self, dataset_id: str, history_id: str | None = None) -> dict[str, Any]:
        """
        Get details about the job that created a specific dataset.

        Args:
            dataset_id: Galaxy dataset ID (encoded)
            history_id: Optional history ID (for performance, not required)

        Returns:
            Job details including tool info, state, and parameters
        """
        decoded_dataset_id = self.trans.security.decode_id(dataset_id)

        # Get the HDA to find its creating job
        from galaxy.managers.hdas import HDAManager

        hda_manager = self.app[HDAManager]
        hda = hda_manager.get_accessible(decoded_dataset_id, self.trans.user)

        if not hda:
            raise ValueError(f"Dataset '{dataset_id}' not found or not accessible")

        job = hda.creating_job
        if not job:
            return {
                "dataset_id": dataset_id,
                "job": None,
                "message": "No creating job found for this dataset",
            }

        return {
            "dataset_id": dataset_id,
            "job_id": self.trans.security.encode_id(job.id),
            "job": {
                "tool_id": job.tool_id,
                "tool_version": job.tool_version,
                "state": job.state,
                "create_time": job.create_time.isoformat() if job.create_time else None,
                "update_time": job.update_time.isoformat() if job.update_time else None,
            },
        }

    def get_job_errors(self, dataset_id: str) -> dict[str, Any]:
        """
        Get error details for a failed job.

        Args:
            dataset_id: Galaxy dataset ID (encoded) of the failed output

        Returns:
            Error details including stderr, stdout, exit_code, and info message
        """
        decoded_dataset_id = self.trans.security.decode_id(dataset_id)

        from galaxy.managers.hdas import HDAManager

        hda_manager = self.app[HDAManager]
        hda = hda_manager.get_accessible(decoded_dataset_id, self.trans.user)

        if not hda:
            raise ValueError(f"Dataset '{dataset_id}' not found or not accessible")

        job = hda.creating_job
        if not job:
            return {
                "dataset_id": dataset_id,
                "error": "No creating job found for this dataset",
            }

        # Truncate large outputs to avoid overwhelming the LLM
        max_output_length = 4000

        stderr = job.stderr or ""
        stdout = job.stdout or ""
        info = job.info or ""

        return {
            "dataset_id": dataset_id,
            "job_id": self.trans.security.encode_id(job.id),
            "tool_id": job.tool_id,
            "tool_version": job.tool_version,
            "state": job.state,
            "exit_code": job.exit_code,
            "info": info[:max_output_length] if info else None,
            "stderr": stderr[:max_output_length] if stderr else None,
            "stdout": stdout[:max_output_length] if stdout else None,
            "truncated": len(stderr) > max_output_length or len(stdout) > max_output_length,
        }

    def download_dataset(self, dataset_id: str) -> dict[str, Any]:
        """
        Get download information for a dataset.

        Since MCP clients are remote, this returns the download URL
        rather than file contents.

        Args:
            dataset_id: Galaxy dataset ID (encoded)

        Returns:
            Download URL and dataset information
        """
        decoded_dataset_id = self.trans.security.decode_id(dataset_id)

        # Get the HDA
        from galaxy.managers.hdas import HDAManager

        hda_manager = self.app[HDAManager]
        hda = hda_manager.get_accessible(decoded_dataset_id, self.trans.user)

        if not hda:
            raise ValueError(f"Dataset '{dataset_id}' not found or not accessible")

        if hda.state != "ok":
            return {
                "dataset_id": dataset_id,
                "state": hda.state,
                "error": f"Dataset is not ready for download (state: {hda.state})",
            }

        # Build download URL
        base_url = getattr(self.app.config, "galaxy_infrastructure_url", "http://localhost:8080")
        download_url = f"{base_url}/api/datasets/{dataset_id}/display"

        return {
            "dataset_id": dataset_id,
            "name": hda.name,
            "extension": hda.extension,
            "file_size": hda.get_size(),
            "state": hda.state,
            "download_url": download_url,
        }

    def get_server_info(self) -> dict[str, Any]:
        """
        Get detailed Galaxy server information.

        Returns:
            Server configuration, version, and capabilities
        """
        config = self.app.config

        return {
            "server": {
                "version": config.version_major,
                "version_minor": getattr(config, "version_minor", ""),
                "brand": getattr(config, "brand", "Galaxy"),
                "url": getattr(config, "galaxy_infrastructure_url", "http://localhost:8080"),
            },
            "capabilities": {
                "allow_user_creation": getattr(config, "allow_user_creation", True),
                "allow_user_dataset_purge": getattr(config, "allow_user_dataset_purge", True),
                "enable_quotas": getattr(config, "enable_quotas", False),
                "support_url": getattr(config, "support_url", ""),
                "terms_url": getattr(config, "terms_url", ""),
            },
        }

    def get_user(self) -> dict[str, Any]:
        """
        Get current user information.

        Returns:
            User details including email, username, and preferences
        """
        user = self.trans.user

        if not user:
            raise ValueError("User must be authenticated")

        return {
            "id": self.trans.security.encode_id(user.id),
            "email": user.email,
            "username": user.username,
            "is_admin": self.trans.user_is_admin,
            "active": user.active,
            "deleted": user.deleted,
            "create_time": user.create_time.isoformat() if user.create_time else None,
        }

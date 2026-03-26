"""
MCP server integration for Galaxy.

Tools are thin wrappers around AgentOperationsManager.
Uses Streamable HTTP transport with stateless mode for multi-worker compatibility.
"""

import logging
from contextlib import contextmanager
from typing import Any

from fastmcp import (
    Context as MCPContext,
    FastMCP,
    settings as fastmcp_settings,
)

from galaxy.managers.users import UserManager
from galaxy.webapps.galaxy.services.agent_operations import AgentOperationsManager
from galaxy.work.context import WorkRequestContext

logger = logging.getLogger(__name__)

logging.getLogger("fakeredis").setLevel(logging.WARNING)
logging.getLogger("docket").setLevel(logging.WARNING)
logging.getLogger("docket.worker").setLevel(logging.WARNING)


def get_mcp_url_builder(fallback_base_url: str):
    """Get a URL builder, using the current HTTP request if available."""
    # Private API -- no public alternative for request-aware URL building in fastmcp yet
    from fastmcp.server.http import _current_http_request

    from galaxy.webapps.galaxy.api import UrlBuilder

    request = _current_http_request.get(None)
    if request is not None:
        return UrlBuilder(request)

    class MCPUrlBuilder:
        """Fallback URL builder when HTTP request is not available."""

        def __init__(self, base_url: str):
            self.base_url = base_url.rstrip("/")

        def __call__(self, name: str, **path_params):
            qualified = path_params.pop("qualified", False)
            query_params = path_params.pop("query_params", None)

            if name == "history":
                history_id = path_params.get("history_id", path_params.get("id", ""))
                url = f"/api/histories/{history_id}"
            elif name == "history_contents":
                history_id = path_params.get("history_id", "")
                url = f"/api/histories/{history_id}/contents"
            elif name == "dataset":
                dataset_id = path_params.get("id", "")
                url = f"/api/datasets/{dataset_id}"
            else:
                url = f"/api/{name}"

            if qualified:
                url = f"{self.base_url}{url}"

            if query_params:
                from urllib.parse import urlencode

                url = f"{url}?{urlencode(query_params)}"

            return url

    return MCPUrlBuilder(fallback_base_url)


@contextmanager
def _mcp_error_handler(operation: str):
    """Standard error handling for MCP tool calls."""
    try:
        yield
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"MCP {operation}: {e}")
        raise ValueError(f"{operation} failed: {e}") from e


def get_mcp_app(gx_app):
    """Create and configure the MCP server application."""
    fastmcp_settings.stateless_http = True

    mcp = FastMCP("Galaxy")

    base_url = getattr(gx_app.config, "galaxy_infrastructure_url", "http://localhost:8080")
    user_manager = UserManager(gx_app)

    def get_operations_manager(api_key: str, ctx: MCPContext) -> AgentOperationsManager:
        """Look up user from API key and return an AgentOperationsManager."""
        if not api_key:
            raise ValueError(
                "API key required. You can create an API key in Galaxy under User -> Preferences -> Manage API Key."
            )

        user = user_manager.by_api_key(api_key=api_key)

        if not user:
            raise ValueError(
                "Invalid API key. Please check your API key and try again. "
                "You can create or view your API key in Galaxy under User -> Preferences -> Manage API Key."
            )

        url_builder = get_mcp_url_builder(base_url)
        trans = WorkRequestContext(app=gx_app, user=user, url_builder=url_builder)

        return AgentOperationsManager(app=gx_app, trans=trans)

    @mcp.tool()
    def connect(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Verify connection to Galaxy and get server information.

        Checks that the API key is valid and returns basic info about
        the Galaxy server and current user.
        """
        with _mcp_error_handler("connect"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.connect()

    @mcp.tool()
    def search_tools(query: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Search for Galaxy tools by name or keyword.

        Matches against tool names, IDs, and descriptions.
        """
        with _mcp_error_handler("search_tools"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.search_tools(query)

    @mcp.tool()
    def get_tool_details(tool_id: str, api_key: str, ctx: MCPContext, io_details: bool = False) -> dict[str, Any]:
        """Get detailed information about a specific Galaxy tool.

        Set io_details=true to get full input/output specifications
        needed for running the tool.
        """
        with _mcp_error_handler("get_tool_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_details(tool_id, io_details)

    @mcp.tool()
    def list_histories(
        api_key: str, ctx: MCPContext, limit: int = 50, offset: int = 0, name: str | None = None
    ) -> dict[str, Any]:
        """List the current user's Galaxy histories.

        Histories are containers for datasets and analysis results.
        Optionally filter by name (substring match).
        """
        with _mcp_error_handler("list_histories"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_histories(limit, offset, name)

    @mcp.tool()
    def run_tool(
        history_id: str, tool_id: str, inputs: dict[str, Any], api_key: str, ctx: MCPContext
    ) -> dict[str, Any]:
        """Execute a Galaxy tool.

        Use get_tool_details() with io_details=true first to learn
        what inputs the tool requires.
        """
        with _mcp_error_handler("run_tool"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.run_tool(history_id, tool_id, inputs)

    @mcp.tool()
    def get_job_status(job_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get the status and details of a Galaxy job.

        Use after run_tool() to check if the job finished and whether
        it succeeded or failed.
        """
        with _mcp_error_handler("get_job_status"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_job_status(job_id)

    @mcp.tool()
    def create_history(name: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Create a new Galaxy history.

        Histories are containers for datasets and analysis results.
        Create one before uploading files or running analyses.
        """
        with _mcp_error_handler("create_history"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.create_history(name)

    @mcp.tool()
    def get_history_details(history_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get detailed information about a specific history.

        Returns metadata and summary stats. Use get_history_contents()
        to get the actual datasets.
        """
        with _mcp_error_handler("get_history_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_history_details(history_id)

    @mcp.tool()
    def get_history_contents(
        history_id: str,
        api_key: str,
        ctx: MCPContext,
        limit: int = 100,
        offset: int = 0,
        order: str = "hid-asc",
        deleted: bool | None = None,
        visible: bool | None = None,
    ) -> dict[str, Any]:
        """Get paginated contents (datasets and collections) from a history.

        Order options: 'hid-asc', 'hid-dsc', 'create_time-dsc',
        'update_time-dsc', 'name-asc'.
        Set deleted=true to include deleted items, visible=false to include hidden items.
        """
        with _mcp_error_handler("get_history_contents"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_history_contents(history_id, limit, offset, order, deleted, visible)

    @mcp.tool()
    def get_dataset_details(dataset_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get detailed information about a specific dataset."""
        with _mcp_error_handler("get_dataset_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_dataset_details(dataset_id)

    @mcp.tool()
    def get_collection_details(
        collection_id: str, api_key: str, ctx: MCPContext, max_elements: int = 500
    ) -> dict[str, Any]:
        """Get detailed information about a dataset collection including its elements.

        Dataset collections group related datasets (e.g., paired-end reads, lists of samples).
        Use max_elements to limit the number of elements returned for large collections.
        """
        with _mcp_error_handler("get_collection_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_collection_details(collection_id, max_elements)

    @mcp.tool()
    def upload_file_from_url(
        history_id: str,
        url: str,
        api_key: str,
        ctx: MCPContext,
        file_type: str = "auto",
        dbkey: str = "?",
        file_name: str | None = None,
    ) -> dict[str, Any]:
        """Upload a file from a URL to Galaxy.

        Runs as an async job; use get_job_status() to monitor progress.
        Common file_types: 'fasta', 'fastq', 'bam', 'vcf', 'bed', 'tabular'.
        """
        with _mcp_error_handler("upload_file_from_url"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.upload_file_from_url(history_id, url, file_type, dbkey, file_name)

    # ==================== Workflow Tools ====================

    @mcp.tool()
    def list_workflows(
        api_key: str,
        ctx: MCPContext,
        limit: int = 50,
        offset: int = 0,
        show_published: bool = False,
        show_shared: bool = True,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List user's workflows with optional filtering."""
        with _mcp_error_handler("list_workflows"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_workflows(limit, offset, show_published, show_shared, search)

    @mcp.tool()
    def get_workflow_details(
        workflow_id: str, api_key: str, ctx: MCPContext, version: int | None = None
    ) -> dict[str, Any]:
        """Get detailed information about a workflow including steps, inputs, and outputs.

        Optionally specify a version number to get a specific workflow version.
        """
        with _mcp_error_handler("get_workflow_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_workflow_details(workflow_id, version)

    @mcp.tool()
    def invoke_workflow(
        workflow_id: str,
        api_key: str,
        ctx: MCPContext,
        history_id: str | None = None,
        inputs: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
        history_name: str | None = None,
    ) -> dict[str, Any]:
        """Invoke (run) a workflow.

        Use get_workflow_details() first to understand required inputs.
        inputs maps workflow input labels/indices to dataset IDs;
        parameters maps step IDs to parameter values.
        Provide history_id to run in an existing history, or history_name
        to create a new history for this invocation.
        """
        with _mcp_error_handler("invoke_workflow"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.invoke_workflow(workflow_id, history_id, inputs, parameters, history_name)

    @mcp.tool()
    def get_invocations(
        api_key: str,
        ctx: MCPContext,
        workflow_id: str | None = None,
        history_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List workflow invocations, optionally filtered by workflow or history."""
        with _mcp_error_handler("get_invocations"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_invocations(workflow_id, history_id, limit, offset)

    @mcp.tool()
    def get_invocation_details(invocation_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get detailed information about a specific workflow invocation."""
        with _mcp_error_handler("get_invocation_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_invocation_details(invocation_id)

    @mcp.tool()
    def cancel_workflow_invocation(invocation_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Cancel a running workflow invocation."""
        with _mcp_error_handler("cancel_workflow_invocation"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.cancel_workflow_invocation(invocation_id)

    # ==================== Tool Enhancement Tools ====================

    @mcp.tool()
    def get_tool_panel(api_key: str, ctx: MCPContext, view: str | None = None) -> dict[str, Any]:
        """Get the tool panel (toolbox) hierarchy of sections and tools."""
        with _mcp_error_handler("get_tool_panel"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_panel(view)

    @mcp.tool()
    def get_tool_run_examples(
        tool_id: str, api_key: str, ctx: MCPContext, tool_version: str | None = None
    ) -> dict[str, Any]:
        """Get test cases showing how to run a tool with real inputs.

        Useful for learning how to properly format tool inputs.
        Optionally specify tool_version to get examples for a specific version.
        """
        with _mcp_error_handler("get_tool_run_examples"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_run_examples(tool_id, tool_version)

    @mcp.tool()
    def get_tool_citations(tool_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get citation information (DOIs, BibTeX) for a tool."""
        with _mcp_error_handler("get_tool_citations"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_citations(tool_id)

    @mcp.tool()
    def search_tools_by_keywords(keywords: list[str], api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Search for tools matching multiple keywords, ranked by relevance.

        More flexible than search_tools: provide multiple keywords and get
        tools matching any of them.
        """
        with _mcp_error_handler("search_tools_by_keywords"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.search_tools_by_keywords(keywords)

    # ==================== Supplementary Tools ====================

    @mcp.tool()
    def list_history_ids(api_key: str, ctx: MCPContext, limit: int = 100) -> dict[str, Any]:
        """Get a simplified list of history IDs and names (lighter than list_histories)."""
        with _mcp_error_handler("list_history_ids"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_history_ids(limit)

    @mcp.tool()
    def get_job_details(
        dataset_id: str, api_key: str, ctx: MCPContext, history_id: str | None = None
    ) -> dict[str, Any]:
        """Get details about the job that created a specific dataset.

        Useful for understanding how a dataset was generated and the
        job's execution status.
        """
        with _mcp_error_handler("get_job_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_job_details(dataset_id, history_id)

    @mcp.tool()
    def download_dataset(dataset_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get download URL and metadata for a dataset.

        The dataset must be in 'ok' state to be downloadable.
        """
        with _mcp_error_handler("download_dataset"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.download_dataset(dataset_id)

    @mcp.tool()
    def get_server_info(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get Galaxy server version, configuration, and capabilities."""
        with _mcp_error_handler("get_server_info"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_server_info()

    @mcp.tool()
    def get_user(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get current authenticated user information."""
        with _mcp_error_handler("get_user"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_user()

    mcp_app = mcp.http_app()
    mcp_app.state.mcp_server = mcp

    logger.info("MCP server initialized (Streamable HTTP)")
    return mcp_app

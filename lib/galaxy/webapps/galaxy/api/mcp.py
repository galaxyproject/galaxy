"""
MCP server integration for Galaxy.

Tools are thin wrappers around AgentOperationsManager.
Uses Streamable HTTP transport with stateless mode for multi-worker compatibility.
"""

import logging
from typing import Any

from fastmcp import (
    Context as MCPContext,
    FastMCP,
    settings as fastmcp_settings,
)

from galaxy.managers.agent_operations import AgentOperationsManager
from galaxy.managers.users import UserManager
from galaxy.work.context import WorkRequestContext

logger = logging.getLogger(__name__)

logging.getLogger("fakeredis").setLevel(logging.WARNING)
logging.getLogger("docket").setLevel(logging.WARNING)
logging.getLogger("docket.worker").setLevel(logging.WARNING)


def get_mcp_url_builder(fallback_base_url: str):
    """Get a URL builder, using the current HTTP request if available."""
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


def get_mcp_app(gx_app):
    """Create and configure the MCP server application."""
    fastmcp_settings.stateless_http = True

    mcp = FastMCP("Galaxy")

    base_url = getattr(gx_app.config, "galaxy_infrastructure_url", "http://localhost:8080")

    def get_operations_manager(api_key: str, ctx: MCPContext) -> AgentOperationsManager:
        """Look up user from API key and return an AgentOperationsManager."""
        if not api_key:
            raise ValueError(
                "API key required. You can create an API key in Galaxy under User -> Preferences -> Manage API Key."
            )

        user_manager = UserManager(gx_app)
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
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.connect()
        except Exception as e:
            logger.error(f"Failed to connect to Galaxy: {str(e)}")
            raise ValueError(f"Failed to connect to Galaxy: {str(e)}") from e

    @mcp.tool()
    def search_tools(query: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Search for Galaxy tools by name or keyword.

        Matches against tool names, IDs, and descriptions.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.search_tools(query)
        except Exception as e:
            logger.error(f"Failed to search tools: {str(e)}")
            raise ValueError(f"Failed to search tools: {str(e)}") from e

    @mcp.tool()
    def get_tool_details(tool_id: str, api_key: str, ctx: MCPContext, io_details: bool = False) -> dict[str, Any]:
        """Get detailed information about a specific Galaxy tool.

        Set io_details=true to get full input/output specifications
        needed for running the tool.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_details(tool_id, io_details)
        except Exception as e:
            logger.error(f"Failed to get tool details for {tool_id}: {str(e)}")
            raise ValueError(f"Failed to get tool details for '{tool_id}': {str(e)}") from e

    @mcp.tool()
    def list_histories(api_key: str, ctx: MCPContext, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """List the current user's Galaxy histories.

        Histories are containers for datasets and analysis results.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_histories(limit, offset)
        except Exception as e:
            logger.error(f"Failed to list histories: {str(e)}")
            raise ValueError(f"Failed to list histories: {str(e)}") from e

    @mcp.tool()
    def run_tool(
        history_id: str, tool_id: str, inputs: dict[str, Any], api_key: str, ctx: MCPContext
    ) -> dict[str, Any]:
        """Execute a Galaxy tool.

        Use get_tool_details() with io_details=true first to learn
        what inputs the tool requires.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.run_tool(history_id, tool_id, inputs)
        except Exception as e:
            logger.error(f"Failed to run tool {tool_id}: {str(e)}")
            raise ValueError(f"Failed to run tool '{tool_id}' in history '{history_id}': {str(e)}") from e

    @mcp.tool()
    def get_job_status(job_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get the status and details of a Galaxy job.

        Use after run_tool() to check if the job finished and whether
        it succeeded or failed.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_job_status(job_id)
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {str(e)}")
            raise ValueError(f"Failed to get status for job '{job_id}': {str(e)}") from e

    @mcp.tool()
    def create_history(name: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Create a new Galaxy history.

        Histories are containers for datasets and analysis results.
        Create one before uploading files or running analyses.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.create_history(name)
        except Exception as e:
            logger.error(f"Failed to create history: {str(e)}")
            raise ValueError(f"Failed to create history '{name}': {str(e)}") from e

    @mcp.tool()
    def get_history_details(history_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get detailed information about a specific history.

        Returns metadata and summary stats. Use get_history_contents()
        to get the actual datasets.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_history_details(history_id)
        except Exception as e:
            logger.error(f"Failed to get history details for {history_id}: {str(e)}")
            raise ValueError(f"Failed to get details for history '{history_id}': {str(e)}") from e

    @mcp.tool()
    def get_history_contents(
        history_id: str,
        api_key: str,
        ctx: MCPContext,
        limit: int = 100,
        offset: int = 0,
        order: str = "hid-asc",
    ) -> dict[str, Any]:
        """Get paginated contents (datasets and collections) from a history.

        Order options: 'hid-asc', 'hid-dsc', 'create_time-dsc',
        'update_time-dsc', 'name-asc'.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_history_contents(history_id, limit, offset, order)
        except Exception as e:
            logger.error(f"Failed to get history contents for {history_id}: {str(e)}")
            raise ValueError(f"Failed to get contents for history '{history_id}': {str(e)}") from e

    @mcp.tool()
    def get_dataset_details(dataset_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get detailed information about a specific dataset."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_dataset_details(dataset_id)
        except Exception as e:
            logger.error(f"Failed to get dataset details for {dataset_id}: {str(e)}")
            raise ValueError(f"Failed to get details for dataset '{dataset_id}': {str(e)}") from e

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
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.upload_file_from_url(history_id, url, file_type, dbkey, file_name)
        except Exception as e:
            logger.error(f"Failed to upload file from URL {url}: {str(e)}")
            raise ValueError(f"Failed to upload file from URL '{url}': {str(e)}") from e

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
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_workflows(limit, offset, show_published, show_shared, search)
        except Exception as e:
            logger.error(f"Failed to list workflows: {str(e)}")
            raise ValueError(f"Failed to list workflows: {str(e)}") from e

    @mcp.tool()
    def get_workflow_details(workflow_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get detailed information about a workflow including steps, inputs, and outputs."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_workflow_details(workflow_id)
        except Exception as e:
            logger.error(f"Failed to get workflow details for {workflow_id}: {str(e)}")
            raise ValueError(f"Failed to get details for workflow '{workflow_id}': {str(e)}") from e

    @mcp.tool()
    def invoke_workflow(
        workflow_id: str,
        history_id: str,
        api_key: str,
        ctx: MCPContext,
        inputs: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke (run) a workflow.

        Use get_workflow_details() first to understand required inputs.
        inputs maps workflow input labels/indices to dataset IDs;
        parameters maps step IDs to parameter values.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.invoke_workflow(workflow_id, history_id, inputs, parameters)
        except Exception as e:
            logger.error(f"Failed to invoke workflow {workflow_id}: {str(e)}")
            raise ValueError(f"Failed to invoke workflow '{workflow_id}': {str(e)}") from e

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
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_invocations(workflow_id, history_id, limit, offset)
        except Exception as e:
            logger.error(f"Failed to get invocations: {str(e)}")
            raise ValueError(f"Failed to get invocations: {str(e)}") from e

    @mcp.tool()
    def get_invocation_details(invocation_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get detailed information about a specific workflow invocation."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_invocation_details(invocation_id)
        except Exception as e:
            logger.error(f"Failed to get invocation details for {invocation_id}: {str(e)}")
            raise ValueError(f"Failed to get details for invocation '{invocation_id}': {str(e)}") from e

    @mcp.tool()
    def cancel_workflow_invocation(invocation_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Cancel a running workflow invocation."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.cancel_workflow_invocation(invocation_id)
        except Exception as e:
            logger.error(f"Failed to cancel invocation {invocation_id}: {str(e)}")
            raise ValueError(f"Failed to cancel invocation '{invocation_id}': {str(e)}") from e

    # ==================== Tool Enhancement Tools ====================

    @mcp.tool()
    def get_tool_panel(api_key: str, ctx: MCPContext, view: str | None = None) -> dict[str, Any]:
        """Get the tool panel (toolbox) hierarchy of sections and tools."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_panel(view)
        except Exception as e:
            logger.error(f"Failed to get tool panel: {str(e)}")
            raise ValueError(f"Failed to get tool panel: {str(e)}") from e

    @mcp.tool()
    def get_tool_run_examples(tool_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get test cases showing how to run a tool with real inputs.

        Useful for learning how to properly format tool inputs.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_run_examples(tool_id)
        except Exception as e:
            logger.error(f"Failed to get tool run examples for {tool_id}: {str(e)}")
            raise ValueError(f"Failed to get run examples for tool '{tool_id}': {str(e)}") from e

    @mcp.tool()
    def get_tool_citations(tool_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get citation information (DOIs, BibTeX) for a tool."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_citations(tool_id)
        except Exception as e:
            logger.error(f"Failed to get tool citations for {tool_id}: {str(e)}")
            raise ValueError(f"Failed to get citations for tool '{tool_id}': {str(e)}") from e

    @mcp.tool()
    def search_tools_by_keywords(keywords: list[str], api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Search for tools matching multiple keywords, ranked by relevance.

        More flexible than search_tools: provide multiple keywords and get
        tools matching any of them.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.search_tools_by_keywords(keywords)
        except Exception as e:
            logger.error(f"Failed to search tools by keywords: {str(e)}")
            raise ValueError(f"Failed to search tools by keywords: {str(e)}") from e

    # ==================== IWC (Intergalactic Workflow Commission) Tools ====================

    @mcp.tool()
    def get_iwc_workflows(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get all workflows from the IWC (Intergalactic Workflow Commission) catalog.

        The IWC maintains curated best-practice Galaxy workflows at iwc.galaxyproject.org.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_iwc_workflows()
        except Exception as e:
            logger.error(f"Failed to get IWC workflows: {str(e)}")
            raise ValueError(f"Failed to get IWC workflows: {str(e)}") from e

    @mcp.tool()
    def search_iwc_workflows(query: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Search IWC workflows by name, description, or tags."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.search_iwc_workflows(query)
        except Exception as e:
            logger.error(f"Failed to search IWC workflows: {str(e)}")
            raise ValueError(f"Failed to search IWC workflows: {str(e)}") from e

    @mcp.tool()
    def import_workflow_from_iwc(trs_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Import a workflow from the IWC catalog into your Galaxy account.

        Use get_iwc_workflows() or search_iwc_workflows() first to find
        the TRS ID of the workflow you want to import.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.import_workflow_from_iwc(trs_id)
        except Exception as e:
            logger.error(f"Failed to import workflow from IWC: {str(e)}")
            raise ValueError(f"Failed to import workflow from IWC (TRS ID: '{trs_id}'): {str(e)}") from e

    # ==================== Supplementary Tools ====================

    @mcp.tool()
    def list_history_ids(api_key: str, ctx: MCPContext, limit: int = 100) -> dict[str, Any]:
        """Get a simplified list of history IDs and names (lighter than list_histories)."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_history_ids(limit)
        except Exception as e:
            logger.error(f"Failed to list history IDs: {str(e)}")
            raise ValueError(f"Failed to list history IDs: {str(e)}") from e

    @mcp.tool()
    def get_job_details(
        dataset_id: str, api_key: str, ctx: MCPContext, history_id: str | None = None
    ) -> dict[str, Any]:
        """Get details about the job that created a specific dataset.

        Useful for understanding how a dataset was generated and the
        job's execution status.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_job_details(dataset_id, history_id)
        except Exception as e:
            logger.error(f"Failed to get job details for dataset {dataset_id}: {str(e)}")
            raise ValueError(f"Failed to get job details for dataset '{dataset_id}': {str(e)}") from e

    @mcp.tool()
    def download_dataset(dataset_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get download URL and metadata for a dataset.

        The dataset must be in 'ok' state to be downloadable.
        """
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.download_dataset(dataset_id)
        except Exception as e:
            logger.error(f"Failed to get download info for dataset {dataset_id}: {str(e)}")
            raise ValueError(f"Failed to get download info for dataset '{dataset_id}': {str(e)}") from e

    @mcp.tool()
    def get_server_info(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get Galaxy server version, configuration, and capabilities."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_server_info()
        except Exception as e:
            logger.error(f"Failed to get server info: {str(e)}")
            raise ValueError(f"Failed to get server info: {str(e)}") from e

    @mcp.tool()
    def get_user(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get current authenticated user information."""
        try:
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_user()
        except Exception as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise ValueError(f"Failed to get user info: {str(e)}") from e

    mcp_app = mcp.http_app()

    logger.info("MCP server initialized with 29 tools (Streamable HTTP)")
    return mcp_app

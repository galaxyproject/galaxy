"""
Model Context Protocol (MCP) server integration for Galaxy.

This module provides MCP tools that allow AI assistants to interact
with Galaxy programmatically. Tools are thin wrappers around the
AgentOperationsManager which provides the actual functionality.
"""

import logging
from typing import Any

from fastmcp import FastMCP

from galaxy.managers.agent_operations import AgentOperationsManager
from galaxy.managers.users import UserManager
from galaxy.work.context import WorkRequestContext

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

    # Helper function to create AgentOperationsManager from API key
    def get_operations_manager(api_key: str) -> AgentOperationsManager:
        """
        Create AgentOperationsManager by converting API key to user context.

        This looks up the user from the API key and creates a WorkRequestContext,
        then returns an AgentOperationsManager in internal mode. This means all
        MCP tools (both external and internal) use the same code path through
        direct Galaxy manager calls.

        Args:
            api_key: Galaxy API key for authentication

        Returns:
            AgentOperationsManager configured for internal mode

        Raises:
            ValueError: If API key is invalid or user not found
        """
        if not api_key:
            raise ValueError(
                "API key required. You can create an API key in Galaxy "
                "under User -> Preferences -> Manage API Key."
            )

        # Look up user from API key
        user_manager = UserManager(gx_app)
        user = user_manager.by_api_key(api_key=api_key)

        if not user:
            raise ValueError(
                "Invalid API key. Please check your API key and try again. "
                "You can create or view your API key in Galaxy under User -> Preferences -> Manage API Key."
            )

        # Create a work context for this user
        trans = WorkRequestContext(app=gx_app, user=user)

        # Return AgentOperationsManager in internal mode
        return AgentOperationsManager(app=gx_app, trans=trans)

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

    @mcp.tool()
    def get_job_status(job_id: str, api_key: str) -> dict[str, Any]:
        """
        Get the status and details of a Galaxy job.

        After running a tool with run_tool(), use this to check if the job has
        finished and whether it succeeded or failed.

        Args:
            job_id: ID of the job to check (from run_tool() response)
            api_key: Galaxy API key for authentication

        Returns:
            Job details including state (queued/running/ok/error), tool info, and timestamps
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_job_status(job_id)
        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {str(e)}")
            raise ValueError(f"Failed to get status for job '{job_id}': {str(e)}") from e

    @mcp.tool()
    def create_history(name: str, api_key: str) -> dict[str, Any]:
        """
        Create a new Galaxy history.

        Histories are containers for datasets and analysis results. Create a new
        history before uploading files or running analyses.

        Args:
            name: Human-readable name for the new history (e.g., 'RNA-seq Analysis')
            api_key: Galaxy API key for authentication

        Returns:
            Created history details including ID, name, and state
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.create_history(name)
        except Exception as e:
            logger.error(f"Failed to create history: {str(e)}")
            raise ValueError(f"Failed to create history '{name}': {str(e)}") from e

    @mcp.tool()
    def get_history_details(history_id: str, api_key: str) -> dict[str, Any]:
        """
        Get detailed information about a specific history.

        Returns history metadata and summary statistics without loading all datasets.
        Use get_history_contents() to get the actual datasets in a history.

        Args:
            history_id: Galaxy history ID (e.g., '1cd8e2f6b131e5aa')
            api_key: Galaxy API key for authentication

        Returns:
            History details including name, state, size, and dataset counts
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_history_details(history_id)
        except Exception as e:
            logger.error(f"Failed to get history details for {history_id}: {str(e)}")
            raise ValueError(f"Failed to get details for history '{history_id}': {str(e)}") from e

    @mcp.tool()
    def get_history_contents(
        history_id: str,
        api_key: str,
        limit: int = 100,
        offset: int = 0,
        order: str = "hid-asc",
    ) -> dict[str, Any]:
        """
        Get paginated contents (datasets and collections) from a specific history.

        Args:
            history_id: Galaxy history ID (e.g., '1cd8e2f6b131e5aa')
            api_key: Galaxy API key for authentication
            limit: Maximum number of items to return per page (default: 100)
            offset: Number of items to skip for pagination (default: 0)
            order: Sort order - options include:
                   'hid-asc' (history ID ascending, oldest first, default)
                   'hid-dsc' (history ID descending, newest first)
                   'create_time-dsc' (creation time descending)
                   'update_time-dsc' (last updated descending)
                   'name-asc' (alphabetical by name)

        Returns:
            List of datasets/collections with pagination metadata
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_history_contents(history_id, limit, offset, order)
        except Exception as e:
            logger.error(f"Failed to get history contents for {history_id}: {str(e)}")
            raise ValueError(f"Failed to get contents for history '{history_id}': {str(e)}") from e

    @mcp.tool()
    def get_dataset_details(dataset_id: str, api_key: str) -> dict[str, Any]:
        """
        Get detailed information about a specific dataset.

        Args:
            dataset_id: Galaxy dataset ID (e.g., 'f2db41e1fa331b3e')
            api_key: Galaxy API key for authentication

        Returns:
            Dataset details including name, state, file size, extension, and metadata
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_dataset_details(dataset_id)
        except Exception as e:
            logger.error(f"Failed to get dataset details for {dataset_id}: {str(e)}")
            raise ValueError(f"Failed to get details for dataset '{dataset_id}': {str(e)}") from e

    @mcp.tool()
    def upload_file_from_url(
        history_id: str,
        url: str,
        api_key: str,
        file_type: str = "auto",
        dbkey: str = "?",
        file_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload a file from a URL to Galaxy.

        Downloads the file from the given URL and uploads it to the specified history.
        The upload runs as an asynchronous job; use get_job_status() to monitor progress.

        Args:
            history_id: Galaxy history ID to upload the file to
            url: URL of the file to upload (e.g., 'https://example.com/data.fasta')
            api_key: Galaxy API key for authentication
            file_type: Galaxy file format name (default: 'auto' for auto-detection)
                      Common types: 'fasta', 'fastq', 'bam', 'vcf', 'bed', 'tabular', 'txt'
            dbkey: Database key/genome build (default: '?')
                   Examples: 'hg38', 'mm10', 'dm6', '?'
            file_name: Optional custom name for the uploaded dataset in Galaxy
                      (inferred from URL if not provided)

        Returns:
            Job information including job ID and output dataset IDs
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.upload_file_from_url(history_id, url, file_type, dbkey, file_name)
        except Exception as e:
            logger.error(f"Failed to upload file from URL {url}: {str(e)}")
            raise ValueError(f"Failed to upload file from URL '{url}': {str(e)}") from e

    # ==================== Workflow Tools ====================

    @mcp.tool()
    def list_workflows(
        api_key: str,
        limit: int = 50,
        offset: int = 0,
        show_published: bool = False,
        show_shared: bool = True,
        search: str | None = None,
    ) -> dict[str, Any]:
        """
        List user's workflows.

        Args:
            api_key: Galaxy API key for authentication
            limit: Maximum number of workflows to return (default: 50)
            offset: Number of workflows to skip for pagination (default: 0)
            show_published: Include publicly published workflows (default: False)
            show_shared: Include workflows shared with the user (default: True)
            search: Optional search term to filter workflows by name

        Returns:
            List of workflows with their IDs, names, and basic metadata
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.list_workflows(limit, offset, show_published, show_shared, search)
        except Exception as e:
            logger.error(f"Failed to list workflows: {str(e)}")
            raise ValueError(f"Failed to list workflows: {str(e)}") from e

    @mcp.tool()
    def get_workflow_details(workflow_id: str, api_key: str) -> dict[str, Any]:
        """
        Get detailed information about a specific workflow.

        Returns workflow metadata, steps, inputs, and outputs.

        Args:
            workflow_id: Galaxy workflow ID (e.g., 'f2db41e1fa331b3e')
            api_key: Galaxy API key for authentication

        Returns:
            Workflow details including name, steps, inputs, outputs, and annotations
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_workflow_details(workflow_id)
        except Exception as e:
            logger.error(f"Failed to get workflow details for {workflow_id}: {str(e)}")
            raise ValueError(f"Failed to get details for workflow '{workflow_id}': {str(e)}") from e

    @mcp.tool()
    def invoke_workflow(
        workflow_id: str,
        history_id: str,
        api_key: str,
        inputs: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Invoke (run) a workflow.

        Use get_workflow_details() first to understand required inputs.

        Args:
            workflow_id: Galaxy workflow ID to run
            history_id: History ID where workflow outputs will be stored
            api_key: Galaxy API key for authentication
            inputs: Dictionary mapping workflow input labels/indices to dataset IDs
                   Example: {'0': {'id': 'dataset_id', 'src': 'hda'}}
            parameters: Dictionary mapping step IDs to parameter values
                       Example: {'step_1': {'param_name': 'value'}}

        Returns:
            Workflow invocation details including invocation ID for monitoring
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.invoke_workflow(workflow_id, history_id, inputs, parameters)
        except Exception as e:
            logger.error(f"Failed to invoke workflow {workflow_id}: {str(e)}")
            raise ValueError(f"Failed to invoke workflow '{workflow_id}': {str(e)}") from e

    @mcp.tool()
    def get_invocations(
        api_key: str,
        workflow_id: str | None = None,
        history_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List workflow invocations.

        Filter by workflow ID or history ID to find specific invocations.

        Args:
            api_key: Galaxy API key for authentication
            workflow_id: Optional workflow ID to filter invocations
            history_id: Optional history ID to filter invocations
            limit: Maximum number of invocations to return (default: 50)
            offset: Number of invocations to skip for pagination (default: 0)

        Returns:
            List of workflow invocations with their states and metadata
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_invocations(workflow_id, history_id, limit, offset)
        except Exception as e:
            logger.error(f"Failed to get invocations: {str(e)}")
            raise ValueError(f"Failed to get invocations: {str(e)}") from e

    @mcp.tool()
    def get_invocation_details(invocation_id: str, api_key: str) -> dict[str, Any]:
        """
        Get detailed information about a specific workflow invocation.

        Args:
            invocation_id: Workflow invocation ID
            api_key: Galaxy API key for authentication

        Returns:
            Invocation details including state, steps, inputs, and outputs
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_invocation_details(invocation_id)
        except Exception as e:
            logger.error(f"Failed to get invocation details for {invocation_id}: {str(e)}")
            raise ValueError(f"Failed to get details for invocation '{invocation_id}': {str(e)}") from e

    @mcp.tool()
    def cancel_workflow_invocation(invocation_id: str, api_key: str) -> dict[str, Any]:
        """
        Cancel a running workflow invocation.

        Args:
            invocation_id: Workflow invocation ID to cancel
            api_key: Galaxy API key for authentication

        Returns:
            Updated invocation details with cancelled state
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.cancel_workflow_invocation(invocation_id)
        except Exception as e:
            logger.error(f"Failed to cancel invocation {invocation_id}: {str(e)}")
            raise ValueError(f"Failed to cancel invocation '{invocation_id}': {str(e)}") from e

    # ==================== Tool Enhancement Tools ====================

    @mcp.tool()
    def get_tool_panel(api_key: str, view: str | None = None) -> dict[str, Any]:
        """
        Get the tool panel (toolbox) structure.

        Returns the hierarchical structure of tool sections and tools
        available in this Galaxy instance.

        Args:
            api_key: Galaxy API key for authentication
            view: Optional panel view name (uses server default if not specified)

        Returns:
            Tool panel hierarchy with sections and tools
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_tool_panel(view)
        except Exception as e:
            logger.error(f"Failed to get tool panel: {str(e)}")
            raise ValueError(f"Failed to get tool panel: {str(e)}") from e

    @mcp.tool()
    def get_tool_run_examples(tool_id: str, api_key: str) -> dict[str, Any]:
        """
        Get test cases/examples showing how to run a tool.

        Returns the tool's test definitions which show real, working input
        configurations. Useful for learning how to properly format tool inputs.

        Args:
            tool_id: Galaxy tool ID (e.g., 'Cut1')
            api_key: Galaxy API key for authentication

        Returns:
            Test cases with example inputs and expected outputs
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_tool_run_examples(tool_id)
        except Exception as e:
            logger.error(f"Failed to get tool run examples for {tool_id}: {str(e)}")
            raise ValueError(f"Failed to get run examples for tool '{tool_id}': {str(e)}") from e

    @mcp.tool()
    def get_tool_citations(tool_id: str, api_key: str) -> dict[str, Any]:
        """
        Get citation information for a tool.

        Returns DOIs, BibTeX entries, and URLs for citing the tool
        in publications.

        Args:
            tool_id: Galaxy tool ID (e.g., 'bwa')
            api_key: Galaxy API key for authentication

        Returns:
            Tool citations including DOIs and BibTeX
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_tool_citations(tool_id)
        except Exception as e:
            logger.error(f"Failed to get tool citations for {tool_id}: {str(e)}")
            raise ValueError(f"Failed to get citations for tool '{tool_id}': {str(e)}") from e

    @mcp.tool()
    def search_tools_by_keywords(keywords: list[str], api_key: str) -> dict[str, Any]:
        """
        Search for tools matching multiple keywords.

        More flexible than search_tools - provide multiple keywords
        and get tools that match any of them, ranked by relevance.

        Args:
            keywords: List of keywords to search for
                     (e.g., ['fastq', 'quality', 'trimming'])
            api_key: Galaxy API key for authentication

        Returns:
            Matching tools sorted by number of keyword matches
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.search_tools_by_keywords(keywords)
        except Exception as e:
            logger.error(f"Failed to search tools by keywords: {str(e)}")
            raise ValueError(f"Failed to search tools by keywords: {str(e)}") from e

    # ==================== IWC (Intergalactic Workflow Commission) Tools ====================

    @mcp.tool()
    def get_iwc_workflows(api_key: str) -> dict[str, Any]:
        """
        Get all workflows from the IWC (Intergalactic Workflow Commission) catalog.

        The IWC maintains a curated collection of best-practice Galaxy workflows
        at iwc.galaxyproject.org. Use this to browse available community workflows.

        Args:
            api_key: Galaxy API key for authentication

        Returns:
            List of IWC workflows with TRS IDs, names, descriptions, and tags
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.get_iwc_workflows()
        except Exception as e:
            logger.error(f"Failed to get IWC workflows: {str(e)}")
            raise ValueError(f"Failed to get IWC workflows: {str(e)}") from e

    @mcp.tool()
    def search_iwc_workflows(query: str, api_key: str) -> dict[str, Any]:
        """
        Search for workflows in the IWC catalog.

        Searches workflow names, descriptions, and tags for matching terms.

        Args:
            query: Search term to find in workflow names, descriptions, or tags
            api_key: Galaxy API key for authentication

        Returns:
            Matching IWC workflows with TRS IDs, names, descriptions, and tags
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.search_iwc_workflows(query)
        except Exception as e:
            logger.error(f"Failed to search IWC workflows: {str(e)}")
            raise ValueError(f"Failed to search IWC workflows: {str(e)}") from e

    @mcp.tool()
    def import_workflow_from_iwc(trs_id: str, api_key: str) -> dict[str, Any]:
        """
        Import a workflow from the IWC catalog into your Galaxy account.

        Use get_iwc_workflows() or search_iwc_workflows() first to find
        the TRS ID of the workflow you want to import.

        Args:
            trs_id: TRS (Tool Registry Service) ID of the IWC workflow
                   (e.g., '#workflow/github.com/iwc-workflows/sars-cov-2-variation-reporting/main')
            api_key: Galaxy API key for authentication

        Returns:
            Imported workflow details including the new Galaxy workflow ID
        """
        try:
            ops_manager = get_operations_manager(api_key)
            return ops_manager.import_workflow_from_iwc(trs_id)
        except Exception as e:
            logger.error(f"Failed to import workflow from IWC: {str(e)}")
            raise ValueError(f"Failed to import workflow from IWC (TRS ID: '{trs_id}'): {str(e)}") from e

    # Create the HTTP app for mounting
    # The path="/mcp" parameter here is just for SSE endpoint naming
    # The actual mount point is determined by fast_app.py
    mcp_app = mcp.sse_app()

    logger.info("MCP server initialized with 24 tools")
    return mcp_app

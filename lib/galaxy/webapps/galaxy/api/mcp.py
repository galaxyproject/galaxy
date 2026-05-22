"""
MCP server integration for Galaxy.

Tools are thin wrappers around AgentOperationsManager.
Uses Streamable HTTP transport with stateless mode for multi-worker compatibility.
"""

import logging
from contextlib import contextmanager
from typing import (
    Any,
    Optional,
)
from urllib.parse import urlparse

from fastmcp import (
    Context as MCPContext,
    FastMCP,
    settings as fastmcp_settings,
)
from starlette.datastructures import URL

from galaxy.agents.operations import AgentOperationsManager
from galaxy.managers.users import UserManager
from galaxy.work.context import (
    GalaxyAbstractRequest,
    GalaxyAbstractResponse,
    SessionRequestContext,
)

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


class _StaticRequest(GalaxyAbstractRequest):
    """Minimal GalaxyAbstractRequest backed by a configured base URL.

    MCP tools run outside of an HTTP request, but downstream serializers
    (notably HDASerializer.serialize_old_display_applications) read
    ``trans.request.base`` to build absolute display-app URLs.
    """

    def __init__(self, base_url: str) -> None:
        # Match GalaxyASGIRequest.base shape (Starlette base_url always has trailing slash).
        self._base = base_url if base_url.endswith("/") else f"{base_url}/"
        self._parsed = urlparse(self._base)

    @property
    def base(self) -> str:
        return self._base

    @property
    def url_path(self) -> str:
        return self._base

    @property
    def host(self) -> str:
        return self._parsed.netloc

    @property
    def is_secure(self) -> bool:
        return self._parsed.scheme == "https"

    def get_cookie(self, name: str) -> Optional[str]:
        return None

    @property
    def url(self) -> URL:
        return URL(self._base)


class _StaticResponse(GalaxyAbstractResponse):
    """No-op GalaxyAbstractResponse for MCP contexts (no HTTP response surface)."""

    def __init__(self) -> None:
        self._headers: dict = {}

    @property
    def headers(self) -> dict:
        return self._headers

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: Optional[int] = None,
        expires: Optional[int] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[str] = "lax",
    ) -> None:
        return None


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

    base_url = gx_app.config.galaxy_infrastructure_url
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
        trans = SessionRequestContext(
            app=gx_app,
            user=user,
            url_builder=url_builder,
            request=_StaticRequest(base_url),
            response=_StaticResponse(),
        )

        return AgentOperationsManager(app=gx_app, trans=trans)

    @mcp.tool()
    def connect(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Verify connection to Galaxy and return server + user information.

        Run this once per session to confirm the API key is valid and learn
        the user's identity, the server URL, and basic capabilities.

        Returns:
            Dict with `connected`, `user` (current user info), and `url`.

        NEXT STEPS:
        - Find tools: search_tools(query) or search_tools_by_keywords(keywords)
        - List or create a history: list_histories() / create_history(name)
        - Browse the toolbox: get_tool_panel()
        """
        with _mcp_error_handler("connect"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.connect()

    @mcp.tool()
    def search_tools(query: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Search Galaxy tools by substring match against name, ID, or description.

        RECOMMENDED WORKFLOW:
        1. Search for tools by name or keyword
        2. Pick a candidate from the results
        3. Call get_tool_details(tool_id, io_details=True) for full input schema
        4. Run the tool with run_tool(history_id, tool_id, inputs)

        Args:
            query: Search query - matches name, ID, or description (case-insensitive).
                Examples: "fastq", "alignment", "filter", "bwa".

        Returns:
            Dict with `tools` (list of matches with id, name, version, description)
            and `count`.

        NEXT STEPS:
        - Inspect a tool: get_tool_details(tool_id, io_details=True)
        - See real test inputs: get_tool_run_examples(tool_id)
        - Multi-keyword search: search_tools_by_keywords(["rna", "alignment"])
        """
        with _mcp_error_handler("search_tools"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.search_tools(query)

    @mcp.tool()
    def get_tool_details(tool_id: str, api_key: str, ctx: MCPContext, io_details: bool = False) -> dict[str, Any]:
        """Get detailed information about a Galaxy tool, including input parameters.

        RECOMMENDED WORKFLOW:
        1. Find tools with search_tools() or get_tool_panel()
        2. Call this with io_details=True to learn input parameter shapes
        3. Build the inputs dict and call run_tool()

        Args:
            tool_id: Tool identifier. Common formats:
                - Built-in: "fastqc", "Cut1", "upload1"
                - Toolshed: "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.73"
            io_details: Set True to include full input/output parameter schemas.
                Required to know how to call run_tool().

        Returns:
            Dict with `id`, `name`, `version`, `description`, plus `inputs` and
            `outputs` schemas when `io_details=True`.

        NEXT STEPS:
        - Find example invocations: get_tool_run_examples(tool_id)
        - Get citations: get_tool_citations(tool_id)
        - Run the tool: run_tool(history_id, tool_id, inputs)

        ERROR HANDLING:
        - Tool not found: verify the ID via search_tools() or get_tool_panel()
        """
        with _mcp_error_handler("get_tool_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_details(tool_id, io_details)

    @mcp.tool()
    def list_histories(
        api_key: str, ctx: MCPContext, limit: int = 50, offset: int = 0, name: str | None = None
    ) -> dict[str, Any]:
        """List the current user's Galaxy histories.

        Histories are Galaxy's primary organizational unit -- each contains
        datasets, collections, and the records of analyses.

        RECOMMENDED WORKFLOW:
        1. List histories to find an existing one, or call create_history() for new work
        2. Use the history_id to upload data or run tools
        3. Inspect contents with get_history_contents(history_id)

        Args:
            limit: Maximum histories to return (default 50). Paginate via `offset`.
            offset: Number to skip from the beginning (default 0).
            name: Substring filter applied to history names (case-insensitive).

        Returns:
            Dict with `histories` (list of {id, name, update_time, ...}) and `count`.

        NEXT STEPS:
        - Lighter listing of just IDs/names: list_history_ids()
        - View a history's contents: get_history_contents(history_id)
        - Create a new history: create_history(name)
        """
        with _mcp_error_handler("list_histories"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_histories(limit, offset, name)

    @mcp.tool()
    def run_tool(
        history_id: str, tool_id: str, inputs: dict[str, Any], api_key: str, ctx: MCPContext
    ) -> dict[str, Any]:
        """Execute a Galaxy tool against datasets in a history.

        RECOMMENDED WORKFLOW:
        1. Pick or create a history: list_histories() / create_history()
        2. Upload data if needed: upload_file_from_url()
        3. Get inputs schema: get_tool_details(tool_id, io_details=True)
        4. Call this function with properly formatted inputs
        5. Monitor with get_job_status(job_id) or get_history_contents()

        Args:
            history_id: Galaxy history ID where outputs will be placed.
            tool_id: Tool identifier (e.g. "fastqc" or a toolshed-qualified ID).
            inputs: Tool input parameters. Common shapes:
                - Dataset: {"input_name": {"src": "hda", "id": "<dataset_id>"}}
                - Collection: {"input_name": {"src": "hdca", "id": "<collection_id>"}}
                - Scalar: {"param_name": value}

        Returns:
            Dict with `jobs` (job objects with id/state) and `outputs` (created
            dataset IDs and names).

        Example:
            run_tool(
                history_id="abc123def456",
                tool_id="fastqc",
                inputs={"input_file": {"src": "hda", "id": "dataset123"}},
            )

        NEXT STEPS:
        - Watch the job: get_job_status(job_id)
        - View outputs: get_history_contents(history_id)
        - Download results: download_dataset(dataset_id)

        ERROR HANDLING:
        - "Tool not found": verify tool_id with search_tools()
        - "Invalid input": re-check shapes with get_tool_details(io_details=True)
        - "Dataset not found": confirm the dataset exists in this history
        """
        with _mcp_error_handler("run_tool"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.run_tool(history_id, tool_id, inputs)

    @mcp.tool()
    def get_job_status(job_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get the status and details of a Galaxy job.

        Use this after run_tool() or invoke_workflow() to check whether the
        job is still running, finished successfully, or failed.

        Args:
            job_id: Galaxy job ID returned by run_tool() or job listings.

        Returns:
            Dict with job state, tool ID, runtime info, and exit code (when finished).

        NEXT STEPS:
        - Inspect the job that produced a dataset: get_job_details(dataset_id)
        - View results: get_history_contents(history_id)
        """
        with _mcp_error_handler("get_job_status"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_job_status(job_id)

    @mcp.tool()
    def create_history(name: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Create a new Galaxy history.

        Each project or analysis usually deserves its own history. Pick a
        descriptive name so the user can find it later in the UI.

        RECOMMENDED WORKFLOW:
        1. Create a history with a descriptive name
        2. Upload inputs: upload_file_from_url()
        3. Run tools or workflows in the new history

        Args:
            name: Human-friendly history name. Examples:
                - "RNA-seq Sample A"
                - "ChIP-seq 2026-05"
                - "BWA alignment of patient_001"

        Returns:
            Dict with the new history's `id`, `name`, and creation metadata.

        NEXT STEPS:
        - Upload data: upload_file_from_url(history_id, url)
        - Run a tool: run_tool(history_id, tool_id, inputs)
        - Run a workflow: invoke_workflow(workflow_id, history_id=...)
        """
        with _mcp_error_handler("create_history"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.create_history(name)

    @mcp.tool()
    def get_history_details(history_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get history metadata and summary stats (no full dataset listing).

        Lightweight overview -- it does NOT page through datasets. For the
        actual datasets, follow up with get_history_contents().

        Args:
            history_id: Galaxy history ID.

        Returns:
            Dict with history metadata (name, state, sizes) and a `contents_summary`
            with total item count.

        NEXT STEPS:
        - List datasets in this history: get_history_contents(history_id)
        - Find a job that created a dataset: get_job_details(dataset_id, history_id)
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
        """List the paginated contents (datasets + collections) of a history.

        Each item carries a `history_content_type` of `dataset` or
        `dataset_collection`. Use the IDs in subsequent dataset/collection calls.

        Args:
            history_id: Galaxy history ID.
            limit: Max items per page (default 100).
            offset: Number of items to skip (default 0).
            order: Sort order. Common values:
                - "hid-asc" (default, oldest first)
                - "hid-dsc" (newest first)
                - "create_time-dsc" / "create_time-asc"
                - "update_time-dsc"
                - "name-asc"
            deleted: True includes deleted items; False excludes them; None uses default.
            visible: False includes hidden items; True excludes them; None uses default.

        Returns:
            Dict with items list, total/returned counts, and pagination info.

        NEXT STEPS:
        - Inspect a dataset: get_dataset_details(dataset_id)
        - Inspect a collection: get_collection_details(collection_id)
        - Download: download_dataset(dataset_id)
        """
        with _mcp_error_handler("get_history_contents"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_history_contents(history_id, limit, offset, order, deleted, visible)

    @mcp.tool()
    def get_dataset_details(dataset_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get detailed information about a single dataset.

        Args:
            dataset_id: Galaxy dataset ID (history dataset association / `hda` ID).

        Returns:
            Dict with dataset metadata: name, state, file size, extension/datatype,
            genome build, and related links.

        NEXT STEPS:
        - Get the creating job: get_job_details(dataset_id)
        - Download the file: download_dataset(dataset_id)
        - For collections, use: get_collection_details(collection_id)
        """
        with _mcp_error_handler("get_dataset_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_dataset_details(dataset_id)

    @mcp.tool()
    def get_collection_details(
        collection_id: str, api_key: str, ctx: MCPContext, max_elements: int = 500
    ) -> dict[str, Any]:
        """Get a dataset collection's metadata and member elements.

        Dataset collections group related datasets together (e.g. paired-end
        reads, sample lists, nested lists of pairs).

        Args:
            collection_id: Galaxy dataset collection ID (`hdca` ID).
            max_elements: Cap on elements returned (default 500). Lower this for
                very large collections.

        Returns:
            Dict with collection metadata (name, type, element count, populated/state)
            and a list of normalized elements with object IDs and per-element metadata.

        NEXT STEPS:
        - Inspect a member: get_dataset_details(object_id)
        - Use as a tool input: pass `{"src": "hdca", "id": collection_id}` to run_tool()
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
        """Upload a file from a URL into a history.

        Galaxy fetches the URL on the server side as an async job. Use the
        returned job/dataset IDs with get_job_status() to monitor progress.

        Args:
            history_id: Destination Galaxy history ID.
            url: Public URL of the file to fetch (e.g. https://.../data.fasta).
            file_type: Galaxy datatype (default "auto" detects from extension).
                Common values: "fasta", "fastq", "bam", "vcf", "bed", "tabular".
            dbkey: Genome build / database key (default "?"). Examples:
                "hg38", "mm10", "dm6".
            file_name: Optional display name; otherwise inferred from the URL.

        Returns:
            Dict with the created upload job and dataset metadata.

        Example:
            upload_file_from_url(
                history_id="abc123",
                url="https://zenodo.org/.../reads.fastq.gz",
                file_type="fastqsanger.gz",
                dbkey="hg38",
            )

        NEXT STEPS:
        - Track the job: get_job_status(job_id)
        - Run a tool on the new dataset: run_tool(history_id, tool_id, inputs)
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
        """List the user's stored Galaxy workflows.

        Args:
            limit: Max workflows to return (default 50).
            offset: Skip this many workflows (default 0).
            show_published: Include workflows published by other users (default False).
            show_shared: Include workflows shared with the user (default True).
            search: Substring filter applied to workflow name/annotation.

        Returns:
            Dict with `workflows` (id, name, tags, update_time, ...) and `count`.

        NEXT STEPS:
        - Inspect a workflow: get_workflow_details(workflow_id)
        - Run a workflow: invoke_workflow(workflow_id, history_id=...)
        - Past runs: get_invocations(workflow_id=...)
        """
        with _mcp_error_handler("list_workflows"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_workflows(limit, offset, show_published, show_shared, search)

    @mcp.tool()
    def get_workflow_details(
        workflow_id: str, api_key: str, ctx: MCPContext, version: int | None = None
    ) -> dict[str, Any]:
        """Get a workflow's full structure: steps, inputs, outputs, parameters.

        Use this before invoke_workflow() to learn the input labels/indices and
        the parameters that can be overridden.

        Args:
            workflow_id: Galaxy workflow ID.
            version: Optional specific workflow version (defaults to latest).

        Returns:
            Dict with workflow metadata and full step/input/output definitions.

        NEXT STEPS:
        - Run it: invoke_workflow(workflow_id, history_id=..., inputs=...)
        - View past runs: get_invocations(workflow_id=workflow_id)
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
        """Invoke (run) a workflow against datasets in a history.

        RECOMMENDED WORKFLOW:
        1. List or pick a workflow: list_workflows()
        2. Inspect the inputs: get_workflow_details(workflow_id)
        3. Provide a history_id (or a history_name to create a new one)
        4. Map inputs and call this function
        5. Track progress with get_invocation_details(invocation_id)

        Args:
            workflow_id: Galaxy workflow ID.
            history_id: Existing history ID for outputs. Mutually exclusive with
                `history_name` -- if both are given, history_id wins.
            inputs: Maps workflow input labels/indices to datasets. Common shape:
                {"<input_label_or_index>": {"src": "hda", "id": "<dataset_id>"}}
                Use "hdca" for collections, "ldda"/"ld" for library datasets.
            parameters: Per-step parameter overrides keyed by step ID.
            history_name: Name to use when creating a new history for this run
                (used only when history_id is None).

        Returns:
            Dict with the new invocation: id, state, history_id, and step info.

        Example:
            invoke_workflow(
                workflow_id="abc123",
                history_id="def456",
                inputs={"0": {"src": "hda", "id": "ds789"}},
            )

        NEXT STEPS:
        - Watch the run: get_invocation_details(invocation_id)
        - Cancel it: cancel_workflow_invocation(invocation_id)
        - View outputs: get_history_contents(history_id)
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
        """List workflow invocations, optionally filtered by workflow or history.

        Args:
            workflow_id: Restrict to invocations of this workflow.
            history_id: Restrict to invocations targeting this history.
            limit: Max invocations returned (default 50).
            offset: Skip this many invocations (default 0).

        Returns:
            Dict with `invocations` (id, state, workflow_id, history_id, ...) and `count`.

        NEXT STEPS:
        - Drill into one: get_invocation_details(invocation_id)
        - Cancel a running one: cancel_workflow_invocation(invocation_id)
        """
        with _mcp_error_handler("get_invocations"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_invocations(workflow_id, history_id, limit, offset)

    @mcp.tool()
    def get_invocation_details(invocation_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get detailed step-level state for a single workflow invocation.

        Args:
            invocation_id: Galaxy workflow invocation ID.

        Returns:
            Dict with invocation state, per-step status, inputs, and outputs.

        NEXT STEPS:
        - Cancel a running invocation: cancel_workflow_invocation(invocation_id)
        - View outputs in the history: get_history_contents(history_id)
        """
        with _mcp_error_handler("get_invocation_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_invocation_details(invocation_id)

    @mcp.tool()
    def cancel_workflow_invocation(invocation_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Cancel a running workflow invocation.

        Already-completed steps remain; not-yet-running steps are skipped.

        Args:
            invocation_id: Galaxy workflow invocation ID.

        Returns:
            Dict confirming cancellation with the updated invocation state.
        """
        with _mcp_error_handler("cancel_workflow_invocation"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.cancel_workflow_invocation(invocation_id)

    # ==================== Tool Enhancement Tools ====================

    @mcp.tool()
    def get_tool_panel(api_key: str, ctx: MCPContext, view: str | None = None) -> dict[str, Any]:
        """Get the toolbox hierarchy of sections and tools.

        Mirrors the left-hand tool panel in Galaxy. Useful for browsing or
        building a category-aware UI.

        Args:
            view: Optional named tool panel view (admin-configured). Defaults to
                the standard panel.

        Returns:
            Dict with the nested section/tool tree.

        NEXT STEPS:
        - Inspect a tool: get_tool_details(tool_id, io_details=True)
        - Search by name: search_tools(query)
        """
        with _mcp_error_handler("get_tool_panel"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_panel(view)

    @mcp.tool()
    def get_tool_run_examples(
        tool_id: str, api_key: str, ctx: MCPContext, tool_version: str | None = None
    ) -> dict[str, Any]:
        """Return XML test definitions (inputs, outputs, assertions) for a tool.

        Galaxy tools ship with test cases that double as worked examples --
        real, runnable input shapes. Read these to learn how to call run_tool().

        Args:
            tool_id: Tool identifier.
            tool_version: Optional version selector (use "*" for all versions).

        Returns:
            Dict with `tool_id`, `requested_version`, and `test_cases`.

        NEXT STEPS:
        - Build a real call: run_tool(history_id, tool_id, inputs)
        """
        with _mcp_error_handler("get_tool_run_examples"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_run_examples(tool_id, tool_version)

    @mcp.tool()
    def get_tool_citations(tool_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get citation information (DOIs, BibTeX) for a Galaxy tool.

        Args:
            tool_id: Tool identifier.

        Returns:
            Dict with `tool_name`, `tool_version`, and `citations` (list of citation
            dicts with type and content).
        """
        with _mcp_error_handler("get_tool_citations"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_tool_citations(tool_id)

    @mcp.tool()
    def search_tools_by_keywords(keywords: list[str], api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Recommend tools by matching multiple keywords across name, description,
        and accepted input formats.

        More flexible than search_tools(): pass several keywords and get tools
        whose name, description, or input format extensions match any of them.

        Args:
            keywords: Keywords or phrases describing what you need. Examples:
                ["csv", "rna", "alignment"], ["fastq", "trim"], ["vcf", "filter"].

        Returns:
            Dict with `tools` (list of slim tool dicts: id, name, description,
            versions) and `count`.

        NEXT STEPS:
        - Inspect a candidate: get_tool_details(tool_id, io_details=True)
        - See real test inputs: get_tool_run_examples(tool_id)
        """
        with _mcp_error_handler("search_tools_by_keywords"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.search_tools_by_keywords(keywords)

    # ==================== Supplementary Tools ====================

    @mcp.tool()
    def list_history_ids(api_key: str, ctx: MCPContext, limit: int = 100) -> dict[str, Any]:
        """Get a simplified list of history IDs and names.

        Lighter than list_histories() -- returns only id/name pairs. Useful when
        you just need to map a history name to an ID.

        Args:
            limit: Max histories to return (default 100).

        Returns:
            Dict with `histories` (list of {id, name}) and `count`.
        """
        with _mcp_error_handler("list_history_ids"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_history_ids(limit)

    @mcp.tool()
    def get_job_details(
        dataset_id: str, api_key: str, ctx: MCPContext, history_id: str | None = None
    ) -> dict[str, Any]:
        """Get details about the job that created a specific dataset.

        Use this when a dataset state is `error` or you want to know exactly
        which tool/parameters produced an output.

        Args:
            dataset_id: Galaxy dataset ID (`hda` ID).
            history_id: Optional history ID to speed up provenance lookup.

        Returns:
            Dict with `job` (full job metadata: tool_id, state, params, runtime),
            plus `dataset_id` and `job_id`.

        NEXT STEPS:
        - Re-run the tool: run_tool(history_id, tool_id, inputs)
        - Inspect dataset details: get_dataset_details(dataset_id)
        """
        with _mcp_error_handler("get_job_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_job_details(dataset_id, history_id)

    @mcp.tool()
    def download_dataset(dataset_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get a dataset's download URL plus basic metadata.

        Returns a signed/qualified URL the client can fetch. The dataset must be
        in `ok` state to be downloadable.

        Args:
            dataset_id: Galaxy dataset ID (`hda` ID).

        Returns:
            Dict with `download_url`, `file_name`, `file_size`, `extension`, and
            related dataset metadata.

        ERROR HANDLING:
        - Dataset not in `ok` state: wait for the producing job to finish
          (use get_job_details(dataset_id) or get_job_status(job_id)).
        """
        with _mcp_error_handler("download_dataset"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.download_dataset(dataset_id)

    @mcp.tool()
    def get_server_info(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get the Galaxy server's version, URL, and selected configuration values.

        Returns:
            Dict with `version`, `url`, and a curated subset of public config flags
            (e.g. enabled features, brand, support links).
        """
        with _mcp_error_handler("get_server_info"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_server_info()

    @mcp.tool()
    def get_user(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get information about the user behind the supplied API key.

        Returns:
            Dict with the user's `id`, `username`, `email`, and quota info.
        """
        with _mcp_error_handler("get_user"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_user()

    # ==================== User-Defined Tools (UDT) ====================

    @mcp.tool()
    def list_user_tools(api_key: str, ctx: MCPContext, active: bool = True) -> dict[str, Any]:
        """List user-defined tools belonging to the current user.

        Args:
            active: If True (default), only show active tools. Set False to
                include deactivated tools.

        Returns:
            Dict with 'tools' (list of user tools, each with id, uuid, tool_id,
            name, and active status) and 'count'.
        """
        with _mcp_error_handler("list_user_tools"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_user_tools(active)

    @mcp.tool()
    def create_user_tool(representation: dict[str, Any], api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Create a user-defined tool in Galaxy from a YAML tool definition.

        User-defined tools are lightweight, containerized tools that can be
        created without admin privileges. They are stored in the database,
        scoped to the creating user, and can be embedded in workflows
        (importing the workflow automatically creates the tool for the
        importing user).

        Requires the USER_TOOL_EXECUTE role on the calling user and
        enable_beta_tool_formats=true in the Galaxy config; both are enforced
        by the underlying manager and surface as permission/config errors here.

        Args:
            representation: The tool definition as a dictionary matching the
                GalaxyUserTool schema. Required fields:
                - class: "GalaxyUserTool" (exactly this string)
                - id: tool identifier (lowercase, no spaces, 3-255 chars)
                - version: version string (e.g. "0.1.0")
                - name: display name shown in Galaxy tool menu
                - container: container image as a STRING (e.g. "python:3.12-slim"),
                  NOT a dict -- this is a common mistake
                - shell_command: the command to execute, with $(inputs.name.path)
                  for data inputs and $(inputs.name) for parameter inputs
                - inputs: list of input dicts, each with "name" and "type"
                  (type can be: "data", "integer", "float", "text", "boolean")
                - outputs: list of output dicts, each with "name", "type": "data",
                  "format" (e.g. "tabular", "vcf", "bed"), and "from_work_dir"

        Returns:
            Dict with the created tool's id, uuid, tool_id, active status, and
            the validated representation.

        Example:
            create_user_tool({
                "class": "GalaxyUserTool",
                "id": "my_filter",
                "version": "0.1.0",
                "name": "My Filter",
                "container": "python:3.12-slim",
                "shell_command": "python3 -c 'import sys; ...'",
                "inputs": [{"name": "input1", "type": "data", "format": "tabular"}],
                "outputs": [
                    {"name": "output1", "type": "data",
                     "format": "tabular", "from_work_dir": "out.tsv"}
                ]
            })

        NEXT STEPS:
        - Run the tool: run_user_tool(history_id, tool_uuid, inputs)
        - List your tools: list_user_tools()
        - Delete a tool: delete_user_tool(uuid)
        """
        with _mcp_error_handler("create_user_tool"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.create_user_tool(representation)

    @mcp.tool()
    def delete_user_tool(uuid: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Deactivate a user-defined tool. Deactivated tools are not loaded into the toolbox.

        Existing job history that referenced the tool is preserved; only
        future runs are blocked.

        Args:
            uuid: The UUID of the tool to deactivate. Get this from list_user_tools().

        Returns:
            Dict confirming deactivation: {"uuid": ..., "deactivated": True}.
        """
        with _mcp_error_handler("delete_user_tool"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.delete_user_tool(uuid)

    @mcp.tool()
    def run_user_tool(
        history_id: str,
        tool_uuid: str,
        inputs: dict[str, Any],
        api_key: str,
        ctx: MCPContext,
    ) -> dict[str, Any]:
        """Run a user-defined tool by UUID, producing outputs in the given history.

        Resolution happens through the tool service's standard run path,
        which accepts tool_uuid in the payload and dispatches via the
        toolbox's unprivileged-tool resolver -- so this is functionally a
        UUID-keyed counterpart to run_tool().

        Args:
            history_id: Galaxy history ID where outputs will be placed.
            tool_uuid: The UUID of the user-defined tool (from create_user_tool
                or list_user_tools).
            inputs: Tool input parameters keyed by input name.
                - Dataset inputs: {"input_name": {"src": "hda", "id": "<dataset_id>"}}
                - Collection inputs: {"input_name": {"src": "hdca", "id": "<collection_id>"}}
                - Scalar parameters: {"param_name": value}

        Returns:
            Dict with job info (job_id, history_id, state) and output dataset IDs.

        Example:
            run_user_tool(
                history_id="abc123",
                tool_uuid="61d15277-a911-45ef-aa66-5385146578cc",
                inputs={
                    "scorer_output": {"src": "hda", "id": "59ace41fc068d3ad"},
                    "top_tracks_per_variant": 5,
                },
            )
        """
        with _mcp_error_handler("run_user_tool"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.run_user_tool(history_id, tool_uuid, inputs)

    # ==================== File sources (remote data repositories) ====================

    @mcp.tool()
    def list_file_source_templates(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """List remote-repository plugin templates Galaxy can connect to.

        Returns templates like Omero, Dropbox, S3, Zenodo, Invenio, Google
        Drive -- the catalog of remote data sources/destinations a user can
        configure. For the user's already-configured instances use
        list_user_file_sources().
        """
        with _mcp_error_handler("list_file_source_templates"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_file_source_templates()

    @mcp.tool()
    def list_user_file_sources(api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """List the current user's configured remote-repository file source instances.

        Each instance is an active connection (Omero server, Dropbox account,
        S3 bucket, etc.) usable as both a data source and an export
        destination. For the catalog of plugin templates use
        list_file_source_templates().
        """
        with _mcp_error_handler("list_user_file_sources"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.list_user_file_sources()

    # ==================== IWC ====================

    @mcp.tool()
    def search_iwc_workflows(query: str, api_key: str, ctx: MCPContext, limit: int = 10) -> dict[str, Any]:
        """Find IWC (Intergalactic Workflows Commission) workflows matching a query or analysis intent.

        IWC hosts curated, best-practice workflows for common bioinformatics
        analyses. Ranks workflows by token overlap against name, description,
        tags, readme, and constituent tool names. Works for both keyword
        queries ("rnaseq") and natural-language intent
        ("I have paired-end RNA-seq and want differential expression").

        RECOMMENDED WORKFLOW:
        1. Search for workflows matching your analysis need
        2. Review the ranked results -- check step_count for complexity,
           readme_summary for details, match_score for ranking confidence
        3. Call get_iwc_workflow_details(trs_id) for full documentation
        4. Import with import_workflow_from_iwc(trs_id)
        5. Run with invoke_workflow()

        Args:
            query: Search query or analysis intent. Case-insensitive. Matches
                against workflow name, description, tags, readme text, and the
                names of tools the workflow uses. Examples:
                - "rnaseq"
                - "variant calling from whole exome sequencing"
                - "assemble a bacterial genome from nanopore reads"
            limit: Maximum number of results to return (default 10).

        Returns:
            Dict with 'query', 'workflows' (ranked, enriched entries), and
            'count'. Each workflow entry includes:
            - trsID: Unique identifier for importing
            - name, description, tags, categories
            - readme_summary: First ~300 chars of documentation
            - step_count: Number of workflow steps (complexity indicator)
            - authors: List of {name, orcid}
            - tools_used: Tool names referenced by the workflow
            - match_score: Token-overlap rank score

        TIP: Be specific. "RNA-seq" matches many workflows, but "differential
        expression RNA-seq human samples" ranks them more usefully.

        NEXT STEPS:
        - Get full details: get_iwc_workflow_details(trs_id)
        - Import to Galaxy: import_workflow_from_iwc(trs_id)
        """
        with _mcp_error_handler("search_iwc_workflows"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.search_iwc_workflows(query, limit)

    @mcp.tool()
    def get_iwc_workflow_details(trs_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Get comprehensive details about a specific IWC workflow before importing.

        Use this to examine a workflow's full documentation, inputs, and
        complexity before deciding to import it into your Galaxy instance.

        RECOMMENDED WORKFLOW:
        1. Find candidates with search_iwc_workflows()
        2. Call this function with the trsID to get full details
        3. Review the readme and inputs to ensure it fits your needs
        4. Import with import_workflow_from_iwc(trs_id)

        Args:
            trs_id: The TRS (Tool Registry Service) ID from search results.
                Format: "#workflow/github.com/iwc-workflows/<name>/<branch>"
                Example: "#workflow/github.com/iwc-workflows/rnaseq-pe/main"

        Returns:
            Dict with comprehensive workflow information:
            - trsID, name, description, tags, categories
            - readme: Full markdown documentation (the real docs)
            - readme_summary: Truncated version for quick scanning
            - step_count: Total number of workflow steps
            - tools_used: Tool names referenced by the workflow
            - authors: List of {name, orcid}

        ERROR HANDLING:
        - "not found": Check trsID spelling; use search_iwc_workflows() to find
          valid IDs.

        NEXT STEPS:
        - Import workflow: import_workflow_from_iwc(trs_id)
        - After import, run with invoke_workflow(workflow_id, inputs)
        """
        with _mcp_error_handler("get_iwc_workflow_details"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.get_iwc_workflow_details(trs_id)

    @mcp.tool()
    def import_workflow_from_iwc(trs_id: str, api_key: str, ctx: MCPContext) -> dict[str, Any]:
        """Import an IWC workflow into the user's stored workflows.

        The workflow is materialized through Galaxy's standard workflow-import
        path (workflow_contents_manager.build_workflow_from_raw_description),
        so it ends up as a private StoredWorkflow owned by the calling user --
        the same shape any other imported workflow has.

        RECOMMENDED WORKFLOW:
        1. Find the workflow with search_iwc_workflows()
        2. Inspect with get_iwc_workflow_details(trs_id) to confirm it's the right one
        3. Import with this tool, then run with invoke_workflow()

        Args:
            trs_id: TRS ID of the workflow in the IWC manifest.
                Format: "#workflow/github.com/iwc-workflows/<name>/<branch>"

        Returns:
            Dict with the imported workflow's id, name, original trsID, and
            `missing_tools` -- a list of tool ids referenced by the workflow
            that are not currently installed in this Galaxy. A non-empty
            missing_tools list means the workflow imported but won't run
            until an admin installs the missing tools.

        ERROR HANDLING:
        - "not found": trsID isn't in the IWC manifest. Use search_iwc_workflows().
        - "no embedded definition": the manifest entry is malformed; report upstream.

        NEXT STEPS:
        - Run the workflow: invoke_workflow(workflow_id, history_id, inputs)
        - Inspect inputs/outputs: get_workflow_details(workflow_id)
        """
        with _mcp_error_handler("import_workflow_from_iwc"):
            ops_manager = get_operations_manager(api_key, ctx)
            return ops_manager.import_workflow_from_iwc(trs_id)

    mcp_app = mcp.http_app(path="/")
    mcp_app.state.mcp_server = mcp

    logger.info("MCP server initialized (Streamable HTTP)")
    return mcp_app

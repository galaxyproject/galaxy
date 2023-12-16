import logging
from typing import List

from fastapi import (
    Path,
    Request,
)

from tool_shed.context import SessionRequestContext
from tool_shed.managers.tools import search
from tool_shed.managers.trs import (
    get_tool,
    service_info as _service_info,
    tool_classes as _tool_classes,
)
from tool_shed.structured_app import ToolShedApp
from tool_shed.util.shed_index import build_index
from tool_shed_client.schema import BuildSearchIndexResponse
from tool_shed_client.schema.trs import (
    Tool,
    ToolClass,
    ToolVersion,
)
from tool_shed_client.schema.trs_service_info import Service
from . import (
    depends,
    DependsOnTrans,
    RepositorySearchPageQueryParam,
    RepositorySearchPageSizeQueryParam,
    Router,
    ToolsIndexQueryParam,
)

log = logging.getLogger(__name__)

router = Router(tags=["tools"])

TOOL_ID_PATH_PARAM: str = Path(
    ...,
    title="GA4GH TRS Tool ID",
    description="See also https://ga4gh.github.io/tool-registry-service-schemas/DataModel/#trs-tool-and-trs-tool-version-ids",
)


@router.get(
    "/api/tools",
    operation_id="tools__index",
)
def index(
    q: str = ToolsIndexQueryParam,
    page: int = RepositorySearchPageQueryParam,
    page_size: int = RepositorySearchPageSizeQueryParam,
    trans: SessionRequestContext = DependsOnTrans,
):
    search_results = search(trans, q, page, page_size)
    return search_results


@router.put(
    "/api/tools/build_search_index",
    operation_id="tools__build_search_index",
    require_admin=True,
)
def build_search_index(app: ToolShedApp = depends(ToolShedApp)) -> BuildSearchIndexResponse:
    """Not part of the stable API, just something to simplify
    bootstrapping tool sheds, scripting, testing, etc...
    """
    config = app.config
    repos_indexed, tools_indexed = build_index(
        config.whoosh_index_dir,
        config.file_path,
        config.hgweb_config_dir,
        config.database_connection,
    )
    return BuildSearchIndexResponse(
        repositories_indexed=repos_indexed,
        tools_indexed=tools_indexed,
    )


@router.get("/api/ga4gh/trs/v2/service-info", operation_id="tools_trs_service_info")
def service_info(request: Request, app: ToolShedApp = depends(ToolShedApp)) -> Service:
    return _service_info(app, request.url)


@router.get("/api/ga4gh/trs/v2/toolClasses", operation_id="tools__trs_tool_classes")
def tool_classes() -> List[ToolClass]:
    return _tool_classes()


@router.get(
    "/api/ga4gh/trs/v2/tools",
    operation_id="tools__trs_index",
)
def trs_index():
    # we probably want to be able to query the database at the
    # tool level and such to do this right?
    return []


@router.get(
    "/api/ga4gh/trs/v2/tools/{tool_id}",
    operation_id="tools__trs_get",
)
def trs_get(
    trans: SessionRequestContext = DependsOnTrans,
    tool_id: str = TOOL_ID_PATH_PARAM,
) -> Tool:
    return get_tool(trans, tool_id)


@router.get(
    "/api/ga4gh/trs/v2/tools/{tool_id}/versions",
    operation_id="tools__trs_get_versions",
)
def trs_get_versions(
    trans: SessionRequestContext = DependsOnTrans,
    tool_id: str = TOOL_ID_PATH_PARAM,
) -> List[ToolVersion]:
    return get_tool(trans, tool_id).versions

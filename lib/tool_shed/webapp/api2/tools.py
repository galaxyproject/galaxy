from tool_shed.context import SessionRequestContext
from tool_shed.managers.tools import search
from tool_shed.structured_app import ToolShedApp
from tool_shed.util.shed_index import build_index
from tool_shed_client.schema import BuildSearchIndexResponse
from . import (
    depends,
    DependsOnTrans,
    RepositorySearchPageQueryParam,
    RepositorySearchPageSizeQueryParam,
    Router,
    ToolsIndexQueryParam,
)

router = Router(tags=["tools"])


@router.cbv
class FastAPITools:
    app: ToolShedApp = depends(ToolShedApp)

    @router.get(
        "/api/tools",
        operation_id="tools__index",
    )
    def index(
        self,
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
    def build_search_index(self) -> BuildSearchIndexResponse:
        """Not part of the stable API, just something to simplify
        bootstrapping tool sheds, scripting, testing, etc...
        """
        config = self.app.config
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

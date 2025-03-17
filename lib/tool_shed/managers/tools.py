import os
import tempfile
from collections import namedtuple
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

from galaxy import exceptions
from galaxy.exceptions import (
    InconsistentApplicationState,
    InternalServerError,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.tool_shed.metadata.metadata_generator import RepositoryMetadataToolDict
from galaxy.tool_shed.util.basic_util import remove_dir
from galaxy.tool_shed.util.hg_util import (
    clone_repository,
    get_changectx_for_changeset,
)
from galaxy.tool_util.model_factory import parse_tool_custom
from galaxy.tool_util.parser import (
    get_tool_source,
    ToolSource,
)
from galaxy.tools.stock import stock_tool_sources
from galaxy.util import relpath
from tool_shed.context import (
    ProvidesRepositoriesContext,
    SessionRequestContext,
)
from tool_shed.util.common_util import generate_clone_url_for
from tool_shed.webapp.model import RepositoryMetadata
from tool_shed.webapp.search.tool_search import ToolSearch
from tool_shed_client.schema import ShedParsedTool
from .repositories import get_repository_revision_metadata_model
from .trs import trs_tool_id_to_repository_metadata

STOCK_TOOL_SOURCES: Optional[Dict[str, Dict[str, ToolSource]]] = None


def search(trans: SessionRequestContext, q: str, page: int = 1, page_size: int = 10) -> dict:
    """
    Perform the search over TS tools index.
    Note that search works over the Whoosh index which you have
    to pre-create with scripts/tool_shed/build_ts_whoosh_index.sh manually.
    Also TS config option toolshed_search_on has to be True and
    whoosh_index_dir has to be specified.
    """
    app = trans.app
    conf = app.config
    if not conf.toolshed_search_on:
        raise exceptions.ConfigDoesNotAllowException(
            "Searching the TS through the API is turned off for this instance."
        )
    if not conf.whoosh_index_dir:
        raise exceptions.ConfigDoesNotAllowException(
            "There is no directory for the search index specified. Please contact the administrator."
        )
    search_term = q.strip()
    if len(search_term) < 1:
        raise exceptions.RequestParameterInvalidException("The search term has to be at least one character long.")

    tool_search = ToolSearch()

    Boosts = namedtuple(
        "Boosts", ["tool_name_boost", "tool_description_boost", "tool_help_boost", "tool_repo_owner_username_boost"]
    )
    boosts = Boosts(
        float(conf.get("tool_name_boost", 1.2)),
        float(conf.get("tool_description_boost", 0.6)),
        float(conf.get("tool_help_boost", 0.4)),
        float(conf.get("tool_repo_owner_username_boost", 0.3)),
    )

    results = tool_search.search(trans.app, search_term, page, page_size, boosts)
    results["hostname"] = trans.repositories_hostname
    return results


def get_repository_metadata_tool_dict(
    trans: ProvidesRepositoriesContext, trs_tool_id: str, tool_version: str
) -> Tuple[RepositoryMetadata, RepositoryMetadataToolDict]:
    if trs_tool_id.count("~") < 2:
        RequestParameterInvalidException(f"Invalid TRS tool id ({trs_tool_id})")

    name, owner, tool_id = trs_tool_id.split("~", 3)
    repository, metadata_by_version = trs_tool_id_to_repository_metadata(trans, trs_tool_id)
    if tool_version not in metadata_by_version:
        raise ObjectNotFound()
    tool_version_repository_metadata: RepositoryMetadata = metadata_by_version[tool_version]
    raw_metadata = tool_version_repository_metadata.metadata
    tool_dicts: List[RepositoryMetadataToolDict] = raw_metadata.get("tools", [])
    for tool_dict in tool_dicts:
        if tool_dict["id"] != tool_id or tool_dict["version"] != tool_version:
            continue
        return tool_version_repository_metadata, tool_dict
    raise ObjectNotFound()


def parsed_tool_model_cached_for(
    trans: ProvidesRepositoriesContext, trs_tool_id: str, tool_version: str, repository_clone_url: Optional[str] = None
) -> ShedParsedTool:
    model_cache = trans.app.model_cache
    parsed_tool = model_cache.get_cache_entry_for(ShedParsedTool, trs_tool_id, tool_version)
    if parsed_tool is not None:
        return parsed_tool
    parsed_tool = parsed_tool_model_for(trans, trs_tool_id, tool_version, repository_clone_url=repository_clone_url)
    model_cache.insert_cache_entry_for(parsed_tool, trs_tool_id, tool_version)
    return parsed_tool


def parsed_tool_model_for(
    trans: ProvidesRepositoriesContext, trs_tool_id: str, tool_version: str, repository_clone_url: Optional[str] = None
) -> ShedParsedTool:
    tool_source, repository_metadata = tool_source_for(
        trans, trs_tool_id, tool_version, repository_clone_url=repository_clone_url
    )
    parsed_tool = parse_tool_custom(tool_source, ShedParsedTool)
    if repository_metadata:
        revision_model = get_repository_revision_metadata_model(
            trans.app, repository_metadata.repository, repository_metadata, recursive=False
        )
        parsed_tool.repository_revision = revision_model
    return parsed_tool


def tool_source_for(
    trans: ProvidesRepositoriesContext, trs_tool_id: str, tool_version: str, repository_clone_url: Optional[str] = None
) -> Tuple[ToolSource, Optional[RepositoryMetadata]]:
    if "~" in trs_tool_id:
        return _shed_tool_source_for(trans, trs_tool_id, tool_version, repository_clone_url)
    else:
        tool_source = _stock_tool_source_for(trs_tool_id, tool_version)
        if tool_source is None:
            raise ObjectNotFound()
        return tool_source, None


def _shed_tool_source_for(
    trans: ProvidesRepositoriesContext, trs_tool_id: str, tool_version: str, repository_clone_url: Optional[str] = None
) -> Tuple[ToolSource, RepositoryMetadata]:
    rval = get_repository_metadata_tool_dict(trans, trs_tool_id, tool_version)
    repository_metadata, tool_version_metadata = rval
    tool_config = tool_version_metadata["tool_config"]

    repo = repository_metadata.repository.hg_repo
    ctx = get_changectx_for_changeset(repo, repository_metadata.changeset_revision)
    work_dir = tempfile.mkdtemp(prefix="tmp-toolshed-tool_source")
    if repository_clone_url is None:
        repository_clone_url = generate_clone_url_for(trans, repository_metadata.repository)
    try:
        cloned_ok, error_message = clone_repository(repository_clone_url, work_dir, str(ctx.rev()))
        if error_message:
            raise InternalServerError("Failed to materialize target repository revision")
        repo_files_dir = repository_metadata.repository.hg_repository_path(trans.app.config.file_path)
        if not repo_files_dir:
            raise InconsistentApplicationState(
                f"Failed to resolve repository path from hgweb_config_manager for [{trs_tool_id}], inconsistent repository state or application configuration"
            )
        repo_rel_tool_path = relpath(tool_config, repo_files_dir)
        path_to_tool = os.path.join(work_dir, repo_rel_tool_path)
        if not os.path.exists(path_to_tool):
            raise InconsistentApplicationState(
                f"Target tool expected at [{path_to_tool}] and not found, inconsistent repository state or application configuration"
            )
        tool_source = get_tool_source(path_to_tool)
        return tool_source, repository_metadata
    finally:
        remove_dir(work_dir)


def _stock_tool_source_for(tool_id: str, tool_version: str) -> Optional[ToolSource]:
    _init_stock_tool_sources()
    assert STOCK_TOOL_SOURCES
    tool_version_sources = STOCK_TOOL_SOURCES.get(tool_id)
    if tool_version_sources is None:
        return None
    return tool_version_sources.get(tool_version)


def _init_stock_tool_sources() -> None:
    global STOCK_TOOL_SOURCES
    if STOCK_TOOL_SOURCES is None:
        STOCK_TOOL_SOURCES = {}
        for tool_source in stock_tool_sources():
            tool_id = tool_source.parse_id()
            tool_version = tool_source.parse_version()
            if tool_id not in STOCK_TOOL_SOURCES:
                STOCK_TOOL_SOURCES[tool_id] = {}
            STOCK_TOOL_SOURCES[tool_id][tool_version] = tool_source

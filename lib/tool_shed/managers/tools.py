import os
import tempfile
from collections import namedtuple
from typing import (
    List,
    Optional,
    Tuple,
)

from galaxy import exceptions
from galaxy.exceptions import (
    InternalServerError,
    ObjectNotFound,
)
from galaxy.tool_shed.metadata.metadata_generator import RepositoryMetadataToolDict
from galaxy.tool_shed.util.basic_util import remove_dir
from galaxy.tool_shed.util.hg_util import (
    clone_repository,
    get_changectx_for_changeset,
)
from galaxy.tool_util.parameters import (
    input_models_for_tool_source,
    tool_parameter_bundle_from_json,
    ToolParameterBundleModel,
)
from galaxy.tool_util.parser import (
    get_tool_source,
    ToolSource,
)
from tool_shed.context import (
    ProvidesRepositoriesContext,
    SessionRequestContext,
)
from tool_shed.util.common_util import generate_clone_url_for
from tool_shed.webapp.model import RepositoryMetadata
from tool_shed.webapp.search.tool_search import ToolSearch
from .trs import trs_tool_id_to_repository_metadata


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


def tool_input_models_cached_for(
    trans: ProvidesRepositoriesContext, trs_tool_id: str, tool_version: str, repository_clone_url: Optional[str] = None
) -> ToolParameterBundleModel:
    tool_state_cache = trans.app.tool_state_cache
    raw_json = tool_state_cache.get_cache_entry_for(trs_tool_id, tool_version)
    if raw_json is not None:
        return tool_parameter_bundle_from_json(raw_json)
    bundle = tool_input_models_for(trans, trs_tool_id, tool_version, repository_clone_url=repository_clone_url)
    tool_state_cache.insert_cache_entry_for(trs_tool_id, tool_version, bundle.dict())
    return bundle


def tool_input_models_for(
    trans: ProvidesRepositoriesContext, trs_tool_id: str, tool_version: str, repository_clone_url: Optional[str] = None
) -> ToolParameterBundleModel:
    tool_source = tool_source_for(trans, trs_tool_id, tool_version, repository_clone_url=repository_clone_url)
    return input_models_for_tool_source(tool_source)


def tool_source_for(
    trans: ProvidesRepositoriesContext, trs_tool_id: str, tool_version: str, repository_clone_url: Optional[str] = None
) -> ToolSource:
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
        path_to_tool = os.path.join(work_dir, tool_config)
        tool_source = get_tool_source(path_to_tool)
        return tool_source
    finally:
        remove_dir(work_dir)

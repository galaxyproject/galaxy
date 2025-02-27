"""
Manager and Serializer for TS repositories.
"""

import json
import logging
from collections import namedtuple
from time import strftime
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import BaseModel
from sqlalchemy import (
    false,
    func,
    select,
)
from sqlalchemy.orm import scoped_session

from galaxy import web
from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    InsufficientPermissionsException,
    InternalServerError,
    MalformedContents,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.tool_shed.util import dependency_display
from galaxy.util import listify
from galaxy.util.tool_shed.encoding_util import tool_shed_encode
from tool_shed.context import (
    ProvidesRepositoriesContext,
    ProvidesUserContext,
)
from tool_shed.metadata import repository_metadata_manager
from tool_shed.repository_types import util as rt_util
from tool_shed.structured_app import ToolShedApp
from tool_shed.util import hg_util
from tool_shed.util.metadata_util import (
    get_all_dependencies,
    get_current_repository_metadata_for_changeset_revision,
    get_metadata_revisions,
    get_next_downloadable_changeset_revision,
    get_repository_metadata_by_changeset_revision,
)
from tool_shed.util.readme_util import build_readme_files_dict
from tool_shed.util.repository_content_util import upload_tar
from tool_shed.util.repository_util import (
    create_repository as low_level_create_repository,
    get_repo_info_dict,
    get_repositories_by_category,
    get_repository_in_tool_shed,
    validate_repository_name,
)
from tool_shed.util.shed_util_common import (
    count_repositories_in_category,
    get_category,
)
from tool_shed.util.tool_util import generate_message_for_invalid_tools
from tool_shed.webapp.model import (
    Repository,
    RepositoryMetadata,
    User,
)
from tool_shed.webapp.model.db import get_repository_by_name_and_owner
from tool_shed.webapp.search.repo_search import RepoSearch
from tool_shed_client.schema import (
    CreateRepositoryRequest,
    DetailedRepository,
    ExtraRepoInfo,
    LegacyInstallInfoTuple,
    PaginatedRepositoryIndexResults,
    Repository as SchemaRepository,
    RepositoryMetadataInstallInfoDict,
    ResetMetadataOnRepositoryResponse,
)
from .categories import get_value_mapper as category_value_mapper

log = logging.getLogger(__name__)


def search(trans: ProvidesUserContext, q: str, page: int = 1, page_size: int = 10):
    """
    Perform the search over TS repositories.
    Note that search works over the Whoosh index which you have
    to pre-create with scripts/tool_shed/build_ts_whoosh_index.sh manually.
    Also TS config option toolshed_search_on has to be True and
    whoosh_index_dir has to be specified.
    """
    app = trans.app
    conf = app.config
    if not conf.toolshed_search_on:
        raise ConfigDoesNotAllowException("Searching the TS through the API is turned off for this instance.")
    if not conf.whoosh_index_dir:
        raise ConfigDoesNotAllowException(
            "There is no directory for the search index specified. Please contact the administrator."
        )

    search_term = q.strip()
    if len(search_term) < 1:
        raise RequestParameterInvalidException("The search term has to be at least one character long.")

    repo_search = RepoSearch()

    Boosts = namedtuple(
        "Boosts",
        [
            "repo_name_boost",
            "repo_description_boost",
            "repo_long_description_boost",
            "repo_homepage_url_boost",
            "repo_remote_repository_url_boost",
            "categories_boost",
            "repo_owner_username_boost",
        ],
    )
    boosts = Boosts(
        float(conf.get("repo_name_boost", 0.9)),
        float(conf.get("repo_description_boost", 0.6)),
        float(conf.get("repo_long_description_boost", 0.5)),
        float(conf.get("repo_homepage_url_boost", 0.3)),
        float(conf.get("repo_remote_repository_url_boost", 0.2)),
        float(conf.get("categories_boost", 0.5)),
        float(conf.get("repo_owner_username_boost", 0.3)),
    )

    results = repo_search.search(trans, search_term, page, page_size, boosts)
    results["hostname"] = deprecated_hostname()
    return results


def deprecated_hostname() -> str:
    return web.url_for("/", qualified=True)

class UpdatesRequest(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    changeset_revision: str
    hexlify: bool = True


def check_updates(app: ToolShedApp, request: UpdatesRequest) -> Union[str, Dict[str, Any]]:
    name = request.name
    owner = request.owner
    changeset_revision = request.changeset_revision
    hexlify_this = request.hexlify
    repository = get_repository_by_name_and_owner(
        app.model.context, name, owner, eagerload_columns=[Repository.downloadable_revisions]
    )
    if repository and repository.downloadable_revisions:
        repository_metadata = get_repository_metadata_by_changeset_revision(
            app, app.security.encode_id(repository.id), changeset_revision
        )
        tool_shed_status_dict = {}
        # Handle repository deprecation.
        tool_shed_status_dict["repository_deprecated"] = str(repository.deprecated)
        tip_revision = repository.downloadable_revisions[0]
        # Handle latest installable revision.
        if changeset_revision == tip_revision:
            tool_shed_status_dict["latest_installable_revision"] = "True"
        else:
            next_installable_revision = get_next_downloadable_changeset_revision(app, repository, changeset_revision)
            if repository_metadata is None:
                if next_installable_revision and next_installable_revision != changeset_revision:
                    tool_shed_status_dict["latest_installable_revision"] = "True"
                else:
                    tool_shed_status_dict["latest_installable_revision"] = "False"
            else:
                if next_installable_revision and next_installable_revision != changeset_revision:
                    tool_shed_status_dict["latest_installable_revision"] = "False"
                else:
                    tool_shed_status_dict["latest_installable_revision"] = "True"
        # Handle revision updates.
        if changeset_revision == tip_revision:
            tool_shed_status_dict["revision_update"] = "False"
        else:
            if repository_metadata is None:
                tool_shed_status_dict["revision_update"] = "True"
            else:
                tool_shed_status_dict["revision_update"] = "False"
        # Handle revision upgrades.
        metadata_revisions = [revision[1] for revision in get_metadata_revisions(app, repository)]
        num_metadata_revisions = len(metadata_revisions)
        for index, metadata_revision in enumerate(metadata_revisions):
            if index == num_metadata_revisions:
                tool_shed_status_dict["revision_upgrade"] = "False"
                break
            if metadata_revision == changeset_revision:
                if num_metadata_revisions - index > 1:
                    tool_shed_status_dict["revision_upgrade"] = "True"
                else:
                    tool_shed_status_dict["revision_upgrade"] = "False"
                break
        return tool_shed_encode(tool_shed_status_dict) if hexlify_this else json.dumps(tool_shed_status_dict)
    return tool_shed_encode({}) if hexlify_this else json.dumps({})


def guid_to_repository(app: ToolShedApp, tool_id: str) -> Repository:
    # tool_id = remove_protocol_and_user_from_clone_url(tool_id)
    shed, _, owner, name, rest = tool_id.split("/", 5)
    return _get_repository_by_name_and_owner(app.model.context, name, owner)


def index_tool_ids(app: ToolShedApp, tool_ids: List[str]) -> Dict[str, Any]:
    repository_found = []
    all_metadata = {}
    for tool_id in tool_ids:
        repository = guid_to_repository(app, tool_id)
        owner = repository.user.username
        name = repository.name
        assert name
        repository = _get_repository_by_name_and_owner(app.model.session, name, owner)
        if not repository:
            log.warning(f"Repository {owner}/{name} does not exist, skipping")
            continue
        for changeset, changehash in repository.installable_revisions(app):
            metadata = get_current_repository_metadata_for_changeset_revision(app, repository, changehash)
            tools: Optional[List[Dict[str, Any]]] = metadata.metadata.get("tools")
            if not tools:
                log.warning(f"Repository {owner}/{name}/{changehash} does not contain valid tools, skipping")
                continue
            for tool_metadata in tools:
                if tool_metadata["guid"] in tool_ids:
                    repository_found.append(f"{int(changeset)}:{changehash}")
            metadata = get_current_repository_metadata_for_changeset_revision(app, repository, changehash)
            if metadata is None:
                continue
            metadata_dict = metadata.to_dict(
                value_mapper={"id": app.security.encode_id, "repository_id": app.security.encode_id}
            )
            metadata_dict["repository"] = repository.to_dict(value_mapper={"id": app.security.encode_id})
            if metadata.has_repository_dependencies:
                metadata_dict["repository_dependencies"] = get_all_dependencies(
                    app, metadata, processed_dependency_links=[]
                )
            else:
                metadata_dict["repository_dependencies"] = []
            if metadata.includes_tool_dependencies:
                metadata_dict["tool_dependencies"] = repository.get_tool_dependencies(app, changehash)
            else:
                metadata_dict["tool_dependencies"] = {}
            if metadata.includes_tools:
                metadata_dict["tools"] = metadata.metadata["tools"]
            all_metadata[f"{int(changeset)}:{changehash}"] = metadata_dict
    if repository_found:
        all_metadata["current_changeset"] = repository_found[0]
        # all_metadata[ 'found_changesets' ] = repository_found
        return all_metadata
    else:
        return {}


class IndexRequest(BaseModel):
    name: Optional[str]
    owner: Optional[str]
    deleted: bool


class PaginatedIndexRequest(IndexRequest):
    page: int
    page_size: int


def index_repositories(app: ToolShedApp, index_request: IndexRequest) -> Repository:
    session = app.model.context
    return list(session.scalars(_get_repositories_by_name_and_owner_and_deleted(index_request)))


def index_repositories_paginated(app: ToolShedApp, index_request: PaginatedIndexRequest) -> PaginatedRepositoryIndexResults:
    session = app.model.context
    print(index_request.owner)
    stmt = _get_repositories_by_name_and_owner_and_deleted(index_request)
    total_results = session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.limit(index_request.page_size).offset((index_request.page - 1) * index_request.page_size)
    results = (to_model(app, r) for r in session.scalars(stmt).all())
    return PaginatedRepositoryIndexResults(
        total_results=total_results,
        page=index_request.page,
        page_size=index_request.page_size,
        hits=list(results),
        hostname=deprecated_hostname(),
    )


def can_manage_repo(trans: ProvidesUserContext, repository: Repository) -> bool:
    security_agent = trans.app.security_agent
    return trans.user_is_admin or security_agent.user_can_administer_repository(trans.user, repository)


def can_update_repo(trans: ProvidesUserContext, repository: Repository) -> bool:
    app = trans.app
    security_agent = app.security_agent
    return can_manage_repo(trans, repository) or security_agent.can_push(app, trans.user, repository)


def get_repository_metadata_for_management(
    trans: ProvidesUserContext, encoded_repository_id: str, changeset_revision: str
) -> RepositoryMetadata:
    repository = get_repository_in_tool_shed(trans.app, encoded_repository_id)
    ensure_can_manage(trans, repository, "Cannot manage target repository")
    revisions = [r for r in repository.metadata_revisions if r.changeset_revision == changeset_revision]
    if len(revisions) != 1:
        raise ObjectNotFound()
    repository_metadata = revisions[0]
    return repository_metadata


def get_install_info(trans: ProvidesRepositoriesContext, name, owner, changeset_revision) -> LegacyInstallInfoTuple:
    app = trans.app
    value_mapper = get_value_mapper(app)
    # Example URL:
    # http://<xyz>/api/repositories/get_repository_revision_install_info?name=<n>&owner=<o>&changeset_revision=<cr>
    if name and owner and changeset_revision:
        # Get the repository information.
        repository = get_repository_by_name_and_owner(
            app.model.context, name, owner, eagerload_columns=[Repository.downloadable_revisions]
        )
        if repository is None:
            log.debug(f"Cannot locate repository {name} owned by {owner}")
            return {}, {}, {}
        encoded_repository_id = app.security.encode_id(repository.id)
        repository_dict: dict = repository.to_dict(view="element", value_mapper=value_mapper)
        repository_dict["url"] = web.url_for(controller="repositories", action="show", id=encoded_repository_id)
        # Get the repository_metadata information.
        repository_metadata = get_repository_metadata_by_changeset_revision(
            app, encoded_repository_id, changeset_revision
        )
        if repository_metadata is None:
            # The changeset_revision column in the repository_metadata table has been updated with a new
            # value value, so find the changeset_revision to which we need to update.
            new_changeset_revision = get_next_downloadable_changeset_revision(app, repository, changeset_revision)
            repository_metadata = get_repository_metadata_by_changeset_revision(
                app, encoded_repository_id, new_changeset_revision
            )
            changeset_revision = new_changeset_revision
        if repository_metadata is not None:
            encoded_repository_metadata_id = app.security.encode_id(repository_metadata.id)
            repository_metadata_dict: RepositoryMetadataInstallInfoDict = cast(
                RepositoryMetadataInstallInfoDict,
                repository_metadata.to_dict(view="collection", value_mapper=value_mapper),
            )
            repository_metadata_dict["url"] = web.url_for(
                controller="repository_revisions", action="show", id=encoded_repository_metadata_id
            )
            if "tools" in repository_metadata.metadata:
                repository_metadata_dict["valid_tools"] = repository_metadata.metadata["tools"]
            # Get the repo_info_dict for installing the repository.
            repo_info_dict: ExtraRepoInfo
            (
                repo_info_dict,
                includes_tools,
                includes_tool_dependencies,
                includes_tools_for_display_in_tool_panel,
                has_repository_dependencies,
                has_repository_dependencies_only_if_compiling_contained_td,
            ) = get_repo_info_dict(trans, encoded_repository_id, changeset_revision)
            return repository_dict, repository_metadata_dict, repo_info_dict
        else:
            log.debug(
                "Unable to locate repository_metadata record for repository id %s and changeset_revision %s",
                repository.id,
                changeset_revision,
            )
            return repository_dict, {}, {}
    else:
        debug_msg = "Error in the Tool Shed repositories API in get_repository_revision_install_info: "
        debug_msg += f"Invalid name {name} or owner {owner} or changeset_revision {changeset_revision} received."
        log.debug(debug_msg)
        return {}, {}, {}


def get_value_mapper(app: ToolShedApp) -> Dict[str, Callable]:
    value_mapper = {
        "id": app.security.encode_id,
        "repository_id": app.security.encode_id,
        "user_id": app.security.encode_id,
    }
    return value_mapper


def get_ordered_installable_revisions(
    app: ToolShedApp, name: Optional[str], owner: Optional[str], tsr_id: Optional[str]
) -> List[str]:
    eagerload_columns = [Repository.downloadable_revisions]
    if None not in [name, owner]:
        # Get the repository information.
        repository = get_repository_by_name_and_owner(
            app.model.context, name, owner, eagerload_columns=eagerload_columns
        )
        if repository is None:
            raise ObjectNotFound(f"No repository named {name} found with owner {owner}")
    elif tsr_id is not None:
        repository = get_repository_in_tool_shed(app, tsr_id, eagerload_columns=eagerload_columns)
    else:
        error_message = "Error in the Tool Shed repositories API in get_ordered_installable_revisions: "
        error_message += "invalid parameters received."
        log.debug(error_message)
        return []
    return [revision[1] for revision in repository.installable_revisions(app, sort_revisions=True)]


def get_repository_metadata_dict(app: ToolShedApp, id: str, recursive: bool, downloadable_only: bool) -> Dict[str, Any]:
    all_metadata = {}
    repository = get_repository_in_tool_shed(app, id, eagerload_columns=[Repository.downloadable_revisions])
    for changeset, changehash in get_metadata_revisions(
        app, repository, sort_revisions=True, downloadable=downloadable_only
    ):
        metadata = get_current_repository_metadata_for_changeset_revision(app, repository, changehash)
        if metadata is None:
            continue
        metadata_dict = metadata.to_dict(
            value_mapper={"id": app.security.encode_id, "repository_id": app.security.encode_id}
        )
        metadata_dict["repository"] = repository.to_dict(
            value_mapper={"id": app.security.encode_id, "user_id": app.security.encode_id}
        )
        if metadata.has_repository_dependencies and recursive:
            metadata_dict["repository_dependencies"] = get_all_dependencies(
                app, metadata, processed_dependency_links=[]
            )
        else:
            metadata_dict["repository_dependencies"] = []
        if metadata.includes_tools:
            metadata_dict["tools"] = metadata.metadata["tools"]
        metadata_dict["invalid_tools"] = metadata.metadata.get("invalid_tools", [])
        all_metadata[f"{int(changeset)}:{changehash}"] = metadata_dict
    return all_metadata


def readmes(app: ToolShedApp, repository: Repository, changeset_revision: str) -> dict:
    encoded_repository_id = app.security.encode_id(repository.id)
    repository_metadata = get_repository_metadata_by_changeset_revision(app, encoded_repository_id, changeset_revision)
    if repository_metadata:
        metadata = repository_metadata.metadata
        if metadata:
            return build_readme_files_dict(app, repository, changeset_revision, repository_metadata.metadata)
    return {}


def reset_metadata_on_repository(trans: ProvidesUserContext, repository_id) -> ResetMetadataOnRepositoryResponse:
    app: ToolShedApp = trans.app

    def handle_repository(trans, start_time, repository):
        results = dict(start_time=start_time, repository_status=[])
        try:
            rmm = repository_metadata_manager.RepositoryMetadataManager(
                trans,
                repository=repository,
                resetting_all_metadata_on_repository=True,
                updating_installed_repository=False,
                persist=False,
            )
            rmm.reset_all_metadata_on_repository_in_tool_shed()
            rmm_invalid_file_tups = rmm.get_invalid_file_tups()
            if rmm_invalid_file_tups:
                message = generate_message_for_invalid_tools(
                    app, rmm_invalid_file_tups, repository, None, as_html=False
                )
                results["status"] = "warning"
            else:
                message = (
                    f"Successfully reset metadata on repository {repository.name} owned by {repository.user.username}"
                )
                results["status"] = "ok"
        except Exception as e:
            message = (
                f"Error resetting metadata on repository {repository.name} owned by {repository.user.username}: {e}"
            )
            results["status"] = "error"
        status = f"{repository.name} : {message}"
        results["repository_status"].append(status)
        return results

    if repository_id is not None:
        repository = get_repository_in_tool_shed(app, repository_id)
        start_time = strftime("%Y-%m-%d %H:%M:%S")
        log.debug(f"{start_time}...resetting metadata on repository {repository.name}")
        results = handle_repository(trans, start_time, repository)
        stop_time = strftime("%Y-%m-%d %H:%M:%S")
        results["stop_time"] = stop_time
    return ResetMetadataOnRepositoryResponse(**results)


def create_repository(trans: ProvidesUserContext, request: CreateRepositoryRequest) -> Repository:
    app: ToolShedApp = trans.app
    user = trans.user
    assert user
    category_ids = listify(request.category_ids)
    name = request.name
    if invalid_message := validate_repository_name(app, name, user):
        raise RequestParameterInvalidException(invalid_message)

    repo, _ = low_level_create_repository(
        app=app,
        name=name,
        type=request.type_,
        description=request.synopsis,
        long_description=request.description,
        user=user,
        category_ids=category_ids,
        remote_repository_url=request.remote_repository_url,
        homepage_url=request.homepage_url,
    )
    return repo


def to_element_dict(app, repository: Repository, include_categories: bool = False) -> Dict[str, Any]:
    value_mapper = get_value_mapper(app)
    repository_dict = repository.to_dict(view="element", value_mapper=value_mapper)
    if include_categories:
        repository_dict["category_ids"] = [app.security.encode_id(x.category.id) for x in repository.categories]
    return repository_dict


def repositories_by_category(
    app: ToolShedApp,
    category_id: str,
    page: Optional[int] = None,
    sort_key: str = "name",
    sort_order: str = "asc",
    installable: bool = True,
):
    category = get_category(app, category_id)
    category_dict: Dict[str, Any]
    if category is None:
        category_dict = dict(message=f"Unable to locate category record for id {str(id)}.", status="error")
        return category_dict
    category_dict = category.to_dict(view="element", value_mapper=category_value_mapper(app))
    category_dict["repository_count"] = count_repositories_in_category(app, category_id)
    repositories = get_repositories_by_category(
        app, category.id, installable=installable, sort_order=sort_order, sort_key=sort_key, page=page
    )
    category_dict["repositories"] = repositories
    return category_dict


def to_model(app, repository: Repository) -> SchemaRepository:
    return SchemaRepository(**to_element_dict(app, repository))


def to_detailed_model(app, repository: Repository) -> DetailedRepository:
    return DetailedRepository(**to_element_dict(app, repository))


def upload_tar_and_set_metadata(
    trans: ProvidesRepositoriesContext,
    host: str,
    repository: Repository,
    uploaded_file,
    commit_message: str,
    dry_run: bool = False,
):
    app = trans.app
    user = trans.user
    assert user
    assert user.username
    repo_dir = repository.repo_path(app)
    tip = repository.tip()
    tar_response = upload_tar(
        trans,
        user.username,
        repository,
        uploaded_file,
        commit_message,
    )
    (
        ok,
        message,
        _,
        content_alert_str,
        _,
        _,
    ) = tar_response
    if ok:
        # Update the repository files for browsing.
        hg_util.update_repository(repo_dir)
        # Get the new repository tip.
        if tip == repository.tip():
            raise MalformedContents("No changes to repository.")
        else:
            rmm = repository_metadata_manager.RepositoryMetadataManager(trans, repository=repository)
            _, error_message = rmm.set_repository_metadata_due_to_new_tip(host, content_alert_str=content_alert_str)
            if error_message:
                raise InternalServerError(error_message)
            dd = dependency_display.DependencyDisplayer(app)
            if str(repository.type) not in [
                rt_util.REPOSITORY_SUITE_DEFINITION,
                rt_util.TOOL_DEPENDENCY_DEFINITION,
            ]:
                # Provide a warning message if a tool_dependencies.xml file is provided, but tool dependencies
                # weren't loaded due to a requirement tag mismatch or some other problem.  Tool dependency
                # definitions can define orphan tool dependencies (no relationship to any tools contained in the
                # repository), so warning messages are important because orphans are always valid.  The repository
                # owner must be warned in case they did not intend to define an orphan dependency, but simply
                # provided incorrect information (tool shed, name owner, changeset_revision) for the definition.
                if repository.metadata_revisions:
                    # A repository's metadata revisions are order descending by update_time, so the zeroth revision
                    # will be the tip just after an upload.
                    metadata_dict = repository.metadata_revisions[0].metadata
                else:
                    metadata_dict = {}
                orphan_message = dd.generate_message_for_orphan_tool_dependencies(repository, metadata_dict)
                if orphan_message:
                    message += orphan_message
    else:
        raise InternalServerError(message)
    return message


def ensure_can_manage(trans: ProvidesUserContext, repository: Repository, error_message: Optional[str] = None) -> None:
    if not can_manage_repo(trans, repository):
        error_message = error_message or "You do not have permission to update this repository."
        raise InsufficientPermissionsException(error_message)


def _get_repository_by_name_and_owner(session: scoped_session, name: str, owner: str):
    stmt = (
        select(Repository)
        .where(Repository.deprecated == false())
        .where(Repository.deleted == false())
        .where(Repository.name == name)
        .where(User.username == owner)
        .where(Repository.user_id == User.id)
        .limit(1)
    )
    return session.scalars(stmt).first()


def _get_repositories_by_name_and_owner_and_deleted(
    index_request: IndexRequest
):
    owner = index_request.owner
    name = index_request.name
    deleted = index_request.deleted
    stmt = select(Repository).where(Repository.deprecated == false()).where(Repository.deleted == deleted)
    if owner is not None:
        stmt = stmt.where(User.username == owner)
        stmt = stmt.where(Repository.user_id == User.id)
    if name is not None:
        stmt = stmt.where(Repository.name == name)
    stmt = stmt.order_by(Repository.name)
    return stmt

import logging
import os

from mercurial import (
    hg,
    ui,
)
from sqlalchemy import (
    false,
    select,
)
from whoosh.writing import AsyncWriter

import tool_shed.webapp.model.mapping as ts_mapping
from galaxy.tool_util.loader_directory import load_tool_elements_from_path
from galaxy.tools.search import get_or_create_index
from galaxy.util import (
    directory_hash_id,
    ExecutionTimer,
    pretty_print_time_interval,
    unicodify,
)
from tool_shed.util.hgweb_config import hgweb_config_manager
from tool_shed.webapp import model
from tool_shed.webapp.search.repo_search import schema as repo_schema
from tool_shed.webapp.search.tool_search import schema as tool_schema

log = logging.getLogger(__name__)


def _get_or_create_index(whoosh_index_dir):
    tool_index_dir = os.path.join(whoosh_index_dir, "tools")
    if not os.path.exists(whoosh_index_dir):
        os.makedirs(whoosh_index_dir)
    if not os.path.exists(tool_index_dir):
        os.makedirs(tool_index_dir)
    return get_or_create_index(whoosh_index_dir, repo_schema), get_or_create_index(tool_index_dir, tool_schema)


def build_index(whoosh_index_dir, file_path, hgweb_config_dir, hgweb_repo_prefix, dburi, **kwargs):
    """
    Build two search indexes simultaneously
    One is for repositories and the other for tools.

    Returns a tuple with number of repos and tools that were indexed.
    """
    model = ts_mapping.init(dburi, engine_options={}, create_tables=False)
    sa_session = model.session
    repo_index, tool_index = _get_or_create_index(whoosh_index_dir)

    repo_index_writer = AsyncWriter(repo_index)
    tool_index_writer = AsyncWriter(tool_index)
    repos_indexed = 0
    tools_indexed = 0

    execution_timer = ExecutionTimer()
    with repo_index.searcher() as searcher:
        for repo in get_repos(sa_session, file_path, hgweb_config_dir, hgweb_repo_prefix, **kwargs):
            if repo is None:
                continue
            tools_list = repo.pop("tools_list")
            repo_id = repo["id"]
            indexed_document = searcher.document(id=repo_id)
            if indexed_document:
                if indexed_document["full_last_updated"] == repo.get("full_last_updated"):
                    # We're done, since we sorted repos by update time
                    break
                else:
                    # Got an update, delete the previous document
                    repo_index_writer.delete_by_term("id", repo_id)

            repo_index_writer.add_document(**repo)

            #  Tools get their own index
            tool_index_writer.delete_by_term("repo_id", repo_id)
            for tool in tools_list:
                tool_contents = tool.copy()
                tool_contents["repo_owner_username"] = repo.get("repo_owner_username")
                tool_contents["repo_name"] = repo.get("name")
                tool_contents["repo_id"] = repo_id
                tool_index_writer.add_document(**tool_contents)
                tools_indexed += 1

            repos_indexed += 1

    tool_index_writer.commit()
    repo_index_writer.commit()

    log.info("Indexed repos: %s, tools: %s", repos_indexed, tools_indexed)
    log.info("Toolbox index finished %s", execution_timer)
    return repos_indexed, tools_indexed


def get_repos(sa_session, file_path, hgweb_config_dir, hgweb_repo_prefix, **kwargs):
    """
    Load repos from DB and included tools from .xml configs.
    """
    hgwcm = hgweb_config_manager
    hgwcm.hgweb_config_dir = hgweb_config_dir
    for repo in get_repositories_for_indexing(sa_session):
        category_names = []
        for rca in get_repo_cat_associations(sa_session, repo.id):
            category = sa_session.get(model.Category, rca.category.id)
            category_names.append(category.name.lower())
        categories = (",").join(category_names)
        repo_id = repo.id
        name = repo.name
        description = repo.description
        long_description = repo.long_description
        homepage_url = repo.homepage_url
        remote_repository_url = repo.remote_repository_url

        times_downloaded = repo.times_downloaded or 0

        repo_owner_username = ""
        if repo.user_id is not None:
            user = sa_session.get(model.User, repo.user_id)
            repo_owner_username = user.username.lower()

        last_updated = pretty_print_time_interval(repo.update_time)
        full_last_updated = repo.update_time.strftime("%Y-%m-%d %I:%M %p")

        # Load all changesets of the repo for lineage.
        try:
            entry = hgwcm.get_entry(os.path.join(hgweb_repo_prefix, repo.user.username, repo.name))
        except Exception:
            return None
        repo_path = os.path.join(hgweb_config_dir, entry)
        hg_repo = hg.repository(ui.ui(), repo_path.encode("utf-8"))
        lineage = []
        for changeset in hg_repo.changelog:
            lineage.append(f"{unicodify(changeset)}:{unicodify(hg_repo[changeset])}")
        repo_lineage = str(lineage)

        #  Parse all the tools within repo for a separate index.
        tools_list = []
        path = os.path.join(file_path, *directory_hash_id(repo.id))
        path = os.path.join(path, "repo_%d" % repo.id)
        if os.path.exists(path):
            tools_list.extend(load_one_dir(path))
            for root, dirs, _files in os.walk(path):
                if ".hg" in dirs:
                    dirs.remove(".hg")
                for dirname in dirs:
                    tools_in_dir = load_one_dir(os.path.join(root, dirname))
                    tools_list.extend(tools_in_dir)

        yield (
            dict(
                id=unicodify(repo_id),
                name=unicodify(name),
                description=unicodify(description),
                long_description=unicodify(long_description),
                homepage_url=unicodify(homepage_url),
                remote_repository_url=unicodify(remote_repository_url),
                repo_owner_username=unicodify(repo_owner_username),
                times_downloaded=unicodify(times_downloaded),
                approved=unicodify("no"),
                last_updated=unicodify(last_updated),
                full_last_updated=unicodify(full_last_updated),
                tools_list=tools_list,
                repo_lineage=unicodify(repo_lineage),
                categories=unicodify(categories),
            )
        )


def debug_handler(path, exc_info):
    """
    By default the underlying tool parsing logs warnings for each exception.
    This is very chatty hence this metod changes it to debug level.
    """
    log.debug(f"Failed to load tool with path {path}.", exc_info=exc_info)


def load_one_dir(path):
    tools_in_dir = []
    tool_elems = load_tool_elements_from_path(path, load_exception_handler=debug_handler)
    if tool_elems:
        for elem in tool_elems:
            root = elem[1].getroot()
            if root.tag == "tool":
                tool = {}
                if root.find("help") is not None:
                    tool.update(dict(help=unicodify(root.find("help").text)))
                if root.find("description") is not None:
                    tool.update(dict(description=unicodify(root.find("description").text)))
                tool.update(
                    dict(
                        id=unicodify(root.attrib.get("id")),
                        name=unicodify(root.attrib.get("name")),
                        version=unicodify(root.attrib.get("version")),
                    )
                )
                tools_in_dir.append(tool)
    return tools_in_dir


def get_repositories_for_indexing(session):
    # Do not index deleted, deprecated, or "tool_dependency_definition" type repositories.
    Repository = model.Repository
    stmt = (
        select(Repository)
        .where(Repository.deleted == false())
        .where(Repository.deprecated == false())
        .where(Repository.type != "tool_dependency_definition")
        .order_by(Repository.update_time.desc())
    )
    return session.scalars(stmt)


def get_repo_cat_associations(session, repository_id):
    stmt = select(model.RepositoryCategoryAssociation).where(
        model.RepositoryCategoryAssociation.repository_id == repository_id
    )
    return session.scalars(stmt)

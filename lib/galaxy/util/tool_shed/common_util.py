import json
import logging
import os
from typing import (
    Optional,
    TYPE_CHECKING,
)
from urllib.parse import urljoin

from routes import url_for
from typing_extensions import Protocol

from galaxy import util
from galaxy.util.tool_shed import encoding_util

if TYPE_CHECKING:
    from .tool_shed_registry import Registry as ToolShedRegistry

log = logging.getLogger(__name__)

REPOSITORY_OWNER = "devteam"


class HasToolShedRegistry(Protocol):
    tool_shed_registry: "ToolShedRegistry"
    name: str


def accumulate_tool_dependencies(tool_shed_accessible, tool_dependencies, all_tool_dependencies):
    if tool_shed_accessible:
        if tool_dependencies:
            for tool_dependency in tool_dependencies:
                if tool_dependency not in all_tool_dependencies:
                    all_tool_dependencies.append(tool_dependency)
    return all_tool_dependencies


def check_tool_tag_set(elem, migrated_tool_configs_dict, missing_tool_configs_dict):
    file_path = elem.get("file", None)
    if file_path:
        name = os.path.basename(file_path)
        for migrated_tool_config in migrated_tool_configs_dict.keys():
            if migrated_tool_config in [file_path, name]:
                missing_tool_configs_dict[name] = migrated_tool_configs_dict[migrated_tool_config]
    return missing_tool_configs_dict


def generate_clone_url_for_installed_repository(app: HasToolShedRegistry, repository) -> str:
    """Generate the URL for cloning a repository that has been installed into a Galaxy instance."""
    tool_shed_url = get_tool_shed_url_from_tool_shed_registry(app, str(repository.tool_shed))
    return util.build_url(tool_shed_url, pathspec=["repos", str(repository.owner), str(repository.name)])


def generate_clone_url_for_repository_in_tool_shed(user, repository) -> str:
    """Generate the URL for cloning a repository that is in the tool shed."""
    base_url = url_for("/", qualified=True).rstrip("/")
    if user:
        protocol, base = base_url.split("://")
        username = f"{user.username}@"
        return f"{protocol}://{username}{base}/repos/{repository.user.username}/{repository.name}"
    else:
        return f"{base_url}/repos/{repository.user.username}/{repository.name}"


def generate_clone_url_from_repo_info_tup(app: HasToolShedRegistry, repo_info_tup) -> str:
    """Generate the URL for cloning a repository given a tuple of toolshed, name, owner, changeset_revision."""
    # Example tuple: ['http://localhost:9009', 'blast_datatypes', 'test', '461a4216e8ab', False]
    (
        toolshed,
        name,
        owner,
        changeset_revision,
        prior_installation_required,
        only_if_compiling_contained_td,
    ) = parse_repository_dependency_tuple(repo_info_tup)
    tool_shed_url = get_tool_shed_url_from_tool_shed_registry(app, toolshed)
    # Don't include the changeset_revision in clone urls.
    return util.build_url(tool_shed_url, pathspec=["repos", owner, name])


def get_repository_dependencies(app, tool_shed_url, repository_name, repository_owner, changeset_revision):
    repository_dependencies_dict = {}
    tool_shed_accessible = True
    params = dict(name=repository_name, owner=repository_owner, changeset_revision=changeset_revision)
    pathspec = ["repository", "get_repository_dependencies"]
    try:
        raw_text = util.url_get(
            tool_shed_url, auth=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
        )
        tool_shed_accessible = True
    except Exception as e:
        tool_shed_accessible = False
        log.warning(
            "The URL\n%s\nraised the exception:\n%s\n",
            util.build_url(tool_shed_url, pathspec=pathspec, params=params),
            e,
        )
    if tool_shed_accessible:
        if len(raw_text) > 2:
            encoded_text = json.loads(util.unicodify(raw_text))
            repository_dependencies_dict = encoding_util.tool_shed_decode(encoded_text)
    return tool_shed_accessible, repository_dependencies_dict


def get_protocol_from_tool_shed_url(tool_shed_url: str) -> str:
    """Return the protocol from the received tool_shed_url if it exists."""
    try:
        if tool_shed_url.find("://") > 0:
            return tool_shed_url.split("://")[0].lower()
    except Exception:
        # We receive a lot of calls here where the tool_shed_url is None.  The container_util uses
        # that value when creating a header row.  If the tool_shed_url is not None, we have a problem.
        if tool_shed_url is not None:
            log.exception("Handled exception getting the protocol from Tool Shed URL %s", str(tool_shed_url))
    # Default to HTTP protocol.
    return "http"


def get_tool_shed_repository_ids(as_string=False, **kwd):
    tsrid = kwd.get("tool_shed_repository_id", None)
    tsridslist = util.listify(kwd.get("tool_shed_repository_ids", None))
    if not tsridslist:
        tsridslist = util.listify(kwd.get("id", None))
    if tsridslist is not None:
        if tsrid is not None and tsrid not in tsridslist:
            tsridslist.append(tsrid)
        if as_string:
            return ",".join(tsridslist)
        return tsridslist
    else:
        tsridslist = util.listify(kwd.get("ordered_tsr_ids", None))
        if tsridslist is not None:
            if as_string:
                return ",".join(tsridslist)
            return tsridslist
    if as_string:
        return ""
    return []


def get_tool_shed_url_from_tool_shed_registry(app: HasToolShedRegistry, tool_shed: str) -> Optional[str]:
    """
    The value of tool_shed is something like: toolshed.g2.bx.psu.edu.  We need the URL to this tool shed, which is
    something like: http://toolshed.g2.bx.psu.edu/
    """
    cleaned_tool_shed = remove_protocol_from_tool_shed_url(tool_shed)
    for shed_url in app.tool_shed_registry.tool_sheds.values():
        if shed_url.find(cleaned_tool_shed) >= 0:
            if shed_url.endswith("/"):
                shed_url = shed_url.rstrip("/")
            return shed_url
    # The tool shed from which the repository was originally installed must no longer be configured in tool_sheds_conf.xml.
    return None


def get_tool_shed_repository_url(app: HasToolShedRegistry, tool_shed: str, owner: str, name: str):
    tool_shed_url = get_tool_shed_url_from_tool_shed_registry(app, tool_shed)
    if tool_shed_url:
        # Append a slash to the tool shed URL, because urlparse.urljoin will eliminate
        # the last part of a URL if it does not end with a forward slash.
        tool_shed_url = f"{tool_shed_url}/"
        return urljoin(tool_shed_url, f"view/{owner}/{name}")
    return tool_shed_url


def get_user_by_username(app, username):
    """Get a user from the database by username."""
    sa_session = app.model.session
    try:
        user = sa_session.query(app.model.User).filter(app.model.User.table.c.username == username).one()
        return user
    except Exception:
        return None


def handle_galaxy_url(trans, **kwd):
    galaxy_url = kwd.get("galaxy_url", None)
    if galaxy_url:
        trans.set_cookie(galaxy_url, name="toolshedgalaxyurl")
    else:
        galaxy_url = trans.get_cookie(name="toolshedgalaxyurl")
    return galaxy_url


def handle_tool_shed_url_protocol(app: HasToolShedRegistry, shed_url: str) -> str:
    """Handle secure and insecure HTTP protocol since they may change over time."""
    try:
        if app.name == "galaxy":
            url = remove_protocol_from_tool_shed_url(shed_url)
            tool_shed_url = get_tool_shed_url_from_tool_shed_registry(app, url)
            assert tool_shed_url
        else:
            tool_shed_url = str(url_for("/", qualified=True)).rstrip("/")
        return tool_shed_url
    except Exception:
        # We receive a lot of calls here where the tool_shed_url is None.  The container_util uses
        # that value when creating a header row.  If the tool_shed_url is not None, we have a problem.
        if shed_url is not None:
            log.exception("Handled exception removing protocol from URL %s", str(shed_url))
        return shed_url


def parse_repository_dependency_tuple(repository_dependency_tuple, contains_error=False):
    # Default both prior_installation_required and only_if_compiling_contained_td to False in cases where metadata should be reset on the
    # repository containing the repository_dependency definition.
    prior_installation_required = "False"
    only_if_compiling_contained_td = "False"
    if contains_error:
        if len(repository_dependency_tuple) == 5:
            tool_shed, name, owner, changeset_revision, error = repository_dependency_tuple
        elif len(repository_dependency_tuple) == 6:
            tool_shed, name, owner, changeset_revision, prior_installation_required, error = repository_dependency_tuple
        elif len(repository_dependency_tuple) == 7:
            (
                tool_shed,
                name,
                owner,
                changeset_revision,
                prior_installation_required,
                only_if_compiling_contained_td,
                error,
            ) = repository_dependency_tuple
        return (
            tool_shed,
            name,
            owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
            error,
        )
    else:
        if len(repository_dependency_tuple) == 4:
            tool_shed, name, owner, changeset_revision = repository_dependency_tuple
        elif len(repository_dependency_tuple) == 5:
            tool_shed, name, owner, changeset_revision, prior_installation_required = repository_dependency_tuple
        elif len(repository_dependency_tuple) == 6:
            (
                tool_shed,
                name,
                owner,
                changeset_revision,
                prior_installation_required,
                only_if_compiling_contained_td,
            ) = repository_dependency_tuple
        return tool_shed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td


def remove_port_from_tool_shed_url(tool_shed_url: str) -> str:
    """Return a partial Tool Shed URL, eliminating the port if it exists."""
    try:
        if tool_shed_url.find(":") > 0:
            # Eliminate the port, if any, since it will result in an invalid directory name.
            new_tool_shed_url = tool_shed_url.split(":")[0]
        else:
            new_tool_shed_url = tool_shed_url
        return new_tool_shed_url.rstrip("/")
    except Exception:
        # We receive a lot of calls here where the tool_shed_url is None.  The container_util uses
        # that value when creating a header row.  If the tool_shed_url is not None, we have a problem.
        if tool_shed_url is not None:
            log.exception("Handled exception removing the port from Tool Shed URL %s", str(tool_shed_url))
        return tool_shed_url


def remove_protocol_and_port_from_tool_shed_url(tool_shed_url: str) -> str:
    """Return a partial Tool Shed URL, eliminating the protocol and/or port if either exists."""
    tool_shed = remove_protocol_from_tool_shed_url(tool_shed_url)
    tool_shed = remove_port_from_tool_shed_url(tool_shed)
    return tool_shed


def remove_protocol_and_user_from_clone_url(repository_clone_url: str) -> str:
    """Return a URL that can be used to clone a repository, eliminating the protocol and user if either exists."""
    if repository_clone_url.find("@") > 0:
        # We have an url that includes an authenticated user, something like:
        # http://test@bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split("@")
        tmp_url = items[1]
    elif repository_clone_url.find("//") > 0:
        # We have an url that includes only a protocol, something like:
        # http://bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split("//")
        tmp_url = items[1]
    else:
        tmp_url = repository_clone_url
    return tmp_url.rstrip("/")


def remove_protocol_from_tool_shed_url(tool_shed_url: str) -> str:
    """Return a partial Tool Shed URL, eliminating the protocol if it exists."""
    return util.remove_protocol_from_url(tool_shed_url)


__all__ = (
    "accumulate_tool_dependencies",
    "check_tool_tag_set",
    "generate_clone_url_for_installed_repository",
    "generate_clone_url_for_repository_in_tool_shed",
    "generate_clone_url_from_repo_info_tup",
    "get_repository_dependencies",
    "get_protocol_from_tool_shed_url",
    "get_tool_shed_repository_ids",
    "get_tool_shed_url_from_tool_shed_registry",
    "get_tool_shed_repository_url",
    "get_user_by_username",
    "handle_galaxy_url",
    "handle_tool_shed_url_protocol",
    "parse_repository_dependency_tuple",
    "remove_port_from_tool_shed_url",
    "remove_protocol_and_port_from_tool_shed_url",
    "remove_protocol_and_user_from_clone_url",
    "remove_protocol_from_tool_shed_url",
)

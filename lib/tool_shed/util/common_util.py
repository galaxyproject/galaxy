from typing import (
    Optional,
    TYPE_CHECKING,
)

from routes import url_for

from galaxy.util.tool_shed.common_util import (
    accumulate_tool_dependencies,
    check_tool_tag_set,
    generate_clone_url_for_installed_repository,
    generate_clone_url_from_repo_info_tup,
    get_protocol_from_tool_shed_url,
    get_repository_dependencies,
    get_tool_shed_repository_ids,
    get_tool_shed_repository_url,
    get_tool_shed_url_from_tool_shed_registry,
    handle_galaxy_url,
    handle_tool_shed_url_protocol,
    parse_repository_dependency_tuple,
    remove_port_from_tool_shed_url,
    remove_protocol_and_port_from_tool_shed_url,
    remove_protocol_and_user_from_clone_url,
    remove_protocol_from_tool_shed_url,
)

if TYPE_CHECKING:
    from tool_shed.context import ProvidesRepositoriesContext
    from tool_shed.webapp.model import (
        Repository,
        User,
    )


def generate_clone_url_for(trans: "ProvidesRepositoriesContext", repository: "Repository") -> str:
    return generate_clone_url_for_repository_in_tool_shed(trans.user, repository, trans.repositories_hostname)


def generate_clone_url_for_repository_in_tool_shed(
    user: Optional["User"], repository: "Repository", hostname: Optional[str] = None
) -> str:
    """Generate the URL for cloning a repository that is in the tool shed."""
    base_url = hostname or url_for("/", qualified=True).rstrip("/")
    return f"{base_url}/repos/{repository.user.username}/{repository.name}"


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
    "handle_galaxy_url",
    "handle_tool_shed_url_protocol",
    "parse_repository_dependency_tuple",
    "remove_port_from_tool_shed_url",
    "remove_protocol_and_port_from_tool_shed_url",
    "remove_protocol_and_user_from_clone_url",
    "remove_protocol_from_tool_shed_url",
)

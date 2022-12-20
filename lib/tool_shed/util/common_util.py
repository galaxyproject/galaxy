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


def generate_clone_url_for_repository_in_tool_shed(user, repository) -> str:
    """Generate the URL for cloning a repository that is in the tool shed."""
    base_url = url_for("/", qualified=True).rstrip("/")
    if user:
        protocol, base = base_url.split("://")
        username = f"{user.username}@"
        return f"{protocol}://{username}{base}/repos/{repository.user.username}/{repository.name}"
    else:
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

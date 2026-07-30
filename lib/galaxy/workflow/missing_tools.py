"""Work out which tools a workflow needs but cannot use, and what could be done about it.

A workflow can refer to a tool Galaxy does not have in three different ways, and they call
for different answers:

- nothing of that tool is installed, so the tool has to be installed;
- another version of the tool is installed and Galaxy considers switching to it safe, so
  the workflow can simply be upgraded;
- another version is installed but the switch is not known to be safe, so the exact version
  should be installed rather than silently substituted.
"""

import json
import logging
from typing import (
    Any,
    TYPE_CHECKING,
)

from galaxy import (
    exceptions,
    util,
)
from galaxy.schema.workflows import (
    InstalledWorkflowToolRepository,
    ToolShedRepositoryReference,
    UnavailableWorkflowTool,
)
from galaxy.tools import get_safe_version
from galaxy.util.tool_shed.common_util import get_tool_shed_url_from_tool_shed_registry

if TYPE_CHECKING:
    from galaxy.managers.context import ProvidesUserContext

log = logging.getLogger(__name__)

# Tool shed tool ids look like <shed>/repos/<owner>/<name>/<tool>/<version>.
SHED_TOOL_ID_PARTS = 6


def parse_shed_tool_id(tool_id: str) -> ToolShedRepositoryReference | None:
    """Recover the repository a tool shed tool id points at, or None for a local tool."""
    if "/repos/" not in tool_id:
        return None
    parts = tool_id.split("/")
    if len(parts) != SHED_TOOL_ID_PARTS:
        # Not something we can turn back into an installable repository.
        log.debug(f"Cannot derive a tool shed repository from tool id [{tool_id}]")
        return None
    tool_shed, _, owner, name, _tool, _version = parts
    return ToolShedRepositoryReference(tool_shed=tool_shed, owner=owner, name=name, changeset_revision=None)


def find_unavailable_tools(trans: "ProvidesUserContext", tools: list[dict[str, Any]]) -> list[UnavailableWorkflowTool]:
    """Describe the tools of ``tools`` that are not installed in the version asked for.

    ``tools`` is what ``WorkflowContentsManager.get_all_tools`` returns, so subworkflows are
    already accounted for.
    """
    toolbox = trans.app.toolbox
    unavailable = []
    for tool_reference in tools:
        tool_id = tool_reference["tool_id"]
        tool_version = tool_reference.get("tool_version")
        tool_uuid = tool_reference.get("tool_uuid")
        if not tool_id and not tool_uuid:
            continue
        if toolbox.has_tool(tool_id, tool_version=tool_version, tool_uuid=tool_uuid, exact=True, user=trans.user):
            continue
        installed_versions = _installed_versions(trans, tool_id)
        unavailable.append(
            UnavailableWorkflowTool(
                tool_id=tool_id,
                tool_version=tool_version,
                tool_uuid=str(tool_uuid) if tool_uuid else None,
                installed_versions=installed_versions,
                substitute_version=_substitute_version(trans, tool_id, tool_version),
                repository=parse_shed_tool_id(tool_id) if tool_id else None,
            )
        )
    return unavailable


def missing_repositories(unavailable_tools: list[UnavailableWorkflowTool]) -> list[ToolShedRepositoryReference]:
    """The distinct tool shed repositories that would have to be installed, in workflow order."""
    repositories: list[ToolShedRepositoryReference] = []
    for tool in unavailable_tools:
        repository = tool.repository
        if repository is None:
            continue
        if not any(_same_repository(repository, seen) for seen in repositories):
            repositories.append(repository)
    return repositories


def _same_repository(left: ToolShedRepositoryReference, right: ToolShedRepositoryReference) -> bool:
    return (left.tool_shed, left.owner, left.name) == (right.tool_shed, right.owner, right.name)


def _installed_versions(trans: "ProvidesUserContext", tool_id: str) -> list[str]:
    if not tool_id:
        return []
    try:
        installed = trans.app.toolbox.get_tool(tool_id, get_all_versions=True, user=trans.user)
    except Exception:
        # A tool id the toolbox cannot even parse is simply not installed.
        return []
    return [tool.version for tool in installed or [] if tool.version]


def _substitute_version(trans: "ProvidesUserContext", tool_id: str, tool_version: str | None) -> str | None:
    """An installed version Galaxy considers a safe stand-in for the requested one."""
    if not tool_id or not tool_version:
        return None
    tool = trans.app.toolbox.get_tool(tool_id, user=trans.user)
    if tool is None:
        return None
    return get_safe_version(tool, tool_version)


def install_workflow_tool_repository(
    trans: "ProvidesUserContext",
    repository: ToolShedRepositoryReference,
    install_options: dict[str, Any],
) -> list[InstalledWorkflowToolRepository]:
    """Install one tool shed repository a workflow needs, resolving the revision if unset.

    Installation is synchronous, so a repository with many dependencies keeps the request
    open for as long as it takes to install.
    """
    from galaxy.tool_shed.galaxy_install.install_manager import InstallRepositoryManager

    app = trans.app
    tool_shed_url = get_tool_shed_url_from_tool_shed_registry(app, repository.tool_shed)
    if not tool_shed_url:
        raise exceptions.RequestParameterInvalidException(
            f"Tool shed '{repository.tool_shed}' is not one this Galaxy is configured to install from."
        )
    changeset_revision = repository.changeset_revision or latest_installable_revision(
        app, tool_shed_url, repository.name, repository.owner
    )
    resolved = repository.model_copy(update={"changeset_revision": changeset_revision})
    installed = InstallRepositoryManager(app).install(
        tool_shed_url, repository.name, repository.owner, changeset_revision, install_options
    )
    if not installed:
        # install() returns nothing when the revision turned out to be installed already.
        return [InstalledWorkflowToolRepository(repository=resolved, status="Installed")]
    return [
        InstalledWorkflowToolRepository(
            repository=resolved,
            status=tool_shed_repository.status,
            error=tool_shed_repository.error_message or None,
        )
        for tool_shed_repository in installed
    ]


def latest_installable_revision(app, tool_shed_url: str, name: str, owner: str) -> str:
    """Ask the tool shed for the newest revision of a repository that can be installed."""
    params = dict(name=name, owner=owner)
    pathspec = ["api", "repositories", "get_ordered_installable_revisions"]
    try:
        raw_text = util.url_get(
            tool_shed_url, auth=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
        )
        revisions = json.loads(util.unicodify(raw_text))
    except Exception as e:
        raise exceptions.MessageException(
            f"Could not ask {tool_shed_url} which revision of {owner}/{name} to install: {util.unicodify(e)}"
        )
    if not revisions:
        raise exceptions.ObjectNotFound(f"{tool_shed_url} has no installable revision of {owner}/{name}.")
    # The shed returns them oldest first.
    return revisions[-1]

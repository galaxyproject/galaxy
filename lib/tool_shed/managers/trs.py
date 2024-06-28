from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Tuple,
)

from starlette.datastructures import URL

from galaxy.exceptions import ObjectNotFound
from galaxy.util.tool_shed.common_util import remove_protocol_and_user_from_clone_url
from galaxy.version import VERSION
from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.structured_app import ToolShedApp
from tool_shed.util.metadata_util import get_current_repository_metadata_for_changeset_revision
from tool_shed.webapp.model import (
    Repository,
    RepositoryMetadata,
)
from tool_shed_client.schema.trs import (
    DescriptorType,
    Tool,
    ToolClass,
    ToolVersion,
)
from tool_shed_client.schema.trs_service_info import (
    Organization,
    Service,
    ServiceType,
)
from tool_shed_client.trs_util import decode_identifier
from .repositories import guid_to_repository

TRS_SERVICE_NAME = "Tool Shed TRS API"
TRS_SERVICE_DESCRIPTION = "Serves tool shed repository tools according to the GA4GH TRS specification"


def service_info(app: ToolShedApp, request_url: URL):
    components = request_url.components
    hostname = components.hostname
    assert hostname
    default_organization_id = ".".join(reversed(hostname.split(".")))
    config = app.config
    organization_id = cast(str, config.ga4gh_service_id or default_organization_id)
    organization_name = cast(str, config.organization_name or organization_id)
    organization_url = cast(str, config.organization_url or f"{components.scheme}://{components.netloc}")

    organization = Organization(
        url=organization_url,
        name=organization_name,
    )
    service_type = ServiceType(
        group="org.ga4gh",
        artifact="trs",
        version="2.1.0",
    )
    extra_kwds = {}
    if environment := config.ga4gh_service_environment:
        extra_kwds["environment"] = environment
    return Service(
        id=organization_id + ".trs",
        name=TRS_SERVICE_NAME,
        description=TRS_SERVICE_DESCRIPTION,
        organization=organization,
        type=service_type,
        version=VERSION,
        **extra_kwds,
    )


def tool_classes() -> List[ToolClass]:
    return [ToolClass(id="galaxy_tool", name="Galaxy Tool", description="Galaxy XML Tools")]


def trs_tool_id_to_guid(trans: ProvidesRepositoriesContext, trs_tool_id: str) -> str:
    guid = decode_identifier(trans.repositories_hostname, trs_tool_id)
    guid = remove_protocol_and_user_from_clone_url(guid)
    return guid


def trs_tool_id_to_repository(trans: ProvidesRepositoriesContext, trs_tool_id: str) -> Repository:
    return guid_to_repository(trans.app, trs_tool_id_to_guid(trans, trs_tool_id))


def get_repository_metadata_by_tool_version(
    app: ToolShedApp, repository: Repository, tool_id: str
) -> Dict[str, RepositoryMetadata]:
    versions = {}
    for _, changeset in repository.installable_revisions(app):
        metadata = get_current_repository_metadata_for_changeset_revision(app, repository, changeset)
        tools: Optional[List[Dict[str, Any]]] = metadata.metadata.get("tools")
        if not tools:
            continue
        for tool_metadata in tools:
            if tool_metadata["id"] != tool_id:
                continue
            versions[tool_metadata["version"]] = metadata
    return versions


def get_tools_for(repository_metadata: RepositoryMetadata) -> List[Dict[str, Any]]:
    tools: Optional[List[Dict[str, Any]]] = repository_metadata.metadata.get("tools")
    assert tools
    return tools


def trs_tool_id_to_repository_metadata(
    trans: ProvidesRepositoriesContext, trs_tool_id: str
) -> Tuple[Repository, Dict[str, RepositoryMetadata]]:
    tool_guid = decode_identifier(trans.repositories_hostname, trs_tool_id)
    tool_guid = remove_protocol_and_user_from_clone_url(tool_guid)
    _, tool_id = tool_guid.rsplit("/", 1)
    repository = guid_to_repository(trans.app, tool_guid)
    app = trans.app
    versions: Dict[str, RepositoryMetadata] = get_repository_metadata_by_tool_version(app, repository, tool_id)
    if not versions:
        raise ObjectNotFound()

    return repository, versions


def get_tool(trans: ProvidesRepositoriesContext, trs_tool_id: str) -> Tool:
    guid = decode_identifier(trans.repositories_hostname, trs_tool_id)
    guid = remove_protocol_and_user_from_clone_url(guid)
    repo_metadata = trs_tool_id_to_repository_metadata(trans, trs_tool_id)
    repository, metadata_by_version = repo_metadata

    repo_owner = repository.user.username
    aliases: List[str] = [guid]
    hostname = remove_protocol_and_user_from_clone_url(trans.repositories_hostname)
    url = f"https://{hostname}/repos/{repo_owner}/{repository.name}"

    versions: List[ToolVersion] = []
    for tool_version_str, _ in metadata_by_version.items():
        version_url = url  # TODO:
        tool_version = ToolVersion(
            author=[repo_owner],
            containerfile=False,
            descriptor_type=[DescriptorType.GALAXY],
            id=tool_version_str,
            url=version_url,
            verified=False,
        )
        versions.append(tool_version)
    return Tool(
        aliases=aliases,
        id=trs_tool_id,
        url=url,
        toolclass=tool_classes()[0],
        organization=repo_owner,
        versions=versions,
    )

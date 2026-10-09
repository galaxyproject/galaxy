from typing import (
    Any,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)
from typing_extensions import (
    TypedDict,
)

from galaxy.tool_util_models import ParsedTool


class Repository(BaseModel):
    # element/collection view on the backend have same keys/impl
    id: str
    name: str
    owner: str
    type: str  # TODO: enum
    remote_repository_url: str | None = None
    homepage_url: str | None = None
    description: str
    user_id: str
    private: bool
    deleted: bool
    times_downloaded: int
    deprecated: bool
    create_time: str
    update_time: str


class DetailedRepository(Repository):
    long_description: str | None


class RepositoryPermissions(BaseModel):
    allow_push: list[str]
    can_manage: bool  # can the requesting user manage the repository
    can_push: bool


class RepositoryRevisionReadmes(RootModel):
    root: dict[str, str]


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str


class User(BaseModel):
    id: str
    username: str


class UserV2(User):
    is_admin: bool


class Category(BaseModel):
    id: str
    name: str
    description: str
    deleted: bool
    repositories: int


class CreateCategoryRequest(BaseModel):
    name: str
    description: str | None = None


class ValidRepostiroyUpdateMessage(BaseModel):
    message: str


class FailedRepositoryUpdateMessage(BaseModel):
    err_msg: str


class GetOrderedInstallableRevisionsRequest(BaseModel):
    name: str
    owner: str


class OrderedInstallableRevisions(RootModel):
    root: list[str]


RepositoryType = Literal[
    "repository_suite_definition",
    "tool_dependency_definition",
    "unrestricted",
]


class CreateRepositoryRequest(BaseModel):
    name: str
    synopsis: str
    description: str | None = None
    remote_repository_url: str | None = None
    homepage_url: str | None = None
    type_: RepositoryType = Field(
        "unrestricted",
        alias="type",
        title="Type",
    )
    category_ids: list[str] | str | None = Field(
        ...,
        alias="category_ids[]",
        title="Category IDs",
    )
    model_config = ConfigDict(populate_by_name=True)


class UpdateRepositoryRequest(BaseModel):
    name: str | None = None
    synopsis: str | None = None
    type_: RepositoryType | None = Field(
        None,
        alias="type",
        title="Type",
    )
    description: str | None = None
    remote_repository_url: str | None = None
    homepage_url: str | None = None
    category_ids: list[str] | None = Field(
        None,
        alias="category_ids",
        title="Category IDs",
    )
    model_config = ConfigDict(populate_by_name=True)


class RepositoryUpdateRequest(BaseModel):
    commit_message: str | None = None


class RepositoryUpdate(RootModel):
    root: ValidRepostiroyUpdateMessage | FailedRepositoryUpdateMessage

    @property
    def is_ok(self):
        return isinstance(self.root, ValidRepostiroyUpdateMessage)


class RepositoryTool(BaseModel):
    # Added back in post v2 in order for the frontend to render
    # tool descriptions on the repository page.
    description: str
    guid: str
    id: str
    name: str
    requirements: list
    tool_config: str
    tool_type: str
    version: str
    # add_to_tool_panel: bool
    # tests: list
    # version_string_cmd: Optional[str]


class InvalidTool(BaseModel):
    tool_config: str
    error_message: str


class RepositoryRevisionMetadata(BaseModel):
    id: str
    repository: Repository
    repository_dependencies: list["RepositoryDependency"]
    tools: list["RepositoryTool"] | None = None
    invalid_tools: list[InvalidTool]
    repository_id: str
    numeric_revision: int
    changeset_revision: str
    malicious: bool
    downloadable: bool
    missing_test_components: bool
    has_repository_dependencies: bool
    includes_tools: bool
    includes_tools_for_display_in_tool_panel: bool
    create_time: str
    # Deprecate these...
    includes_tool_dependencies: bool | None = None
    includes_datatypes: bool | None = None
    includes_workflows: bool | None = None


class RepositoryDependency(RepositoryRevisionMetadata):
    # This only needs properties for tests it seems?
    # e.g. test_0550_metadata_updated_dependencies.py
    pass


class RepositoryMetadata(RootModel):
    root: dict[str, RepositoryRevisionMetadata]

    @property
    def latest_revision(self) -> RepositoryRevisionMetadata:
        return list(self.root.values())[-1]

    @property
    def tip(self) -> str:
        if self.is_new:
            return "000000000000"
        else:
            return self.latest_revision.changeset_revision

    @property
    def is_new(self) -> bool:
        return len(self.root) == 0


class RepositoryRevisionMetadataPreview(BaseModel):
    """Like RepositoryRevisionMetadata but with Optional fields for dry-run/preview scenarios.

    During reset_metadata dry-run, metadata objects are created in-memory but not persisted,
    so they lack database IDs. The numeric_revision may also be unavailable for newly-pushed
    changesets that haven't been indexed yet.
    """

    id: str | None = None
    repository: Repository
    repository_dependencies: list["RepositoryDependency"]
    tools: list["RepositoryTool"] | None = None
    invalid_tools: list[InvalidTool] = []
    repository_id: str | None = None
    numeric_revision: int | None = None
    changeset_revision: str
    malicious: bool
    downloadable: bool
    missing_test_components: bool
    has_repository_dependencies: bool
    includes_tools: bool
    includes_tools_for_display_in_tool_panel: bool
    create_time: str | None = None
    includes_tool_dependencies: bool | None = None
    includes_datatypes: bool | None = None
    includes_workflows: bool | None = None


class RepositoryMetadataPreview(RootModel):
    """Like RepositoryMetadata but uses RepositoryRevisionMetadataPreview for dry-run scenarios."""

    root: dict[str, RepositoryRevisionMetadataPreview]


class ResetMetadataOnRepositoryRequest(BaseModel):
    repository_id: str
    dry_run: bool = False
    verbose: bool = False


class ChangesetMetadataStatus(BaseModel):
    """Per-changeset detail during reset metadata operation."""

    changeset_revision: str
    numeric_revision: int
    comparison_result: str | None = None  # "initial", "equal", "subset", "not_equal_and_not_subset", "no_metadata"
    record_operation: Literal["created", "updated"] | None = None
    has_tools: bool = False
    has_repository_dependencies: bool = False
    has_tool_dependencies: bool = False
    error: str | None = None


class ResetMetadataOnRepositoryResponse(BaseModel):
    status: str  # TODO: enum...
    repository_status: list[str]
    start_time: str
    stop_time: str
    dry_run: bool = False
    changeset_details: list[ChangesetMetadataStatus] | None = None
    # Full metadata snapshots for diffing (only when verbose=True)
    # Uses Preview types since dry-run objects may lack IDs
    repository_metadata_before: Optional["RepositoryMetadataPreview"] = None
    repository_metadata_after: Optional["RepositoryMetadataPreview"] = None


# Ugh - use with care - param descriptions scraped from older version of the API.
class ResetMetadataOnRepositoriesRequest(BaseModel):
    my_writable: bool = Field(
        False,
        description="""if the API key is associated with an admin user in the Tool Shed, setting this param value
to True will restrict resetting metadata to only repositories that are writable by the user
in addition to those repositories of type tool_dependency_definition.  This param is ignored
if the current user is not an admin user, in which case this same restriction is automatic.""",
    )
    encoded_ids_to_skip: list[str] | None = Field(
        None, description="a list of encoded repository ids for repositories that should not be processed"
    )


class ResetMetadataOnRepositoriesResponse(BaseModel):
    repository_status: list[str]
    start_time: str
    stop_time: str


class ToolSearchRequest(BaseModel):
    q: str
    page: int | None = None
    page_size: int | None = None


class ToolSearchHitTool(BaseModel):
    id: str
    repo_owner_username: str
    repo_name: str
    name: str
    description: str


class ToolSearchHit(BaseModel):
    tool: ToolSearchHitTool
    matched_terms: dict[str, Any]
    score: float


class ToolSearchResults(BaseModel):
    # These next three really should be ints :<
    total_results: str
    page: str
    page_size: str
    hostname: str
    hits: list[ToolSearchHit]

    def find_search_hit(self, repository: Repository) -> ToolSearchHit | None:
        matching_hit: ToolSearchHit | None = None

        for hit in self.hits:
            owner_matches = hit.tool.repo_owner_username == repository.owner
            name_matches = hit.tool.repo_name == repository.name
            if owner_matches and name_matches:
                matching_hit = hit
                break

        return matching_hit


IndexSortByType = Literal["name", "create_time"]


class RepositoryIndexRequest(BaseModel):
    filter: str | None = None
    owner: str | None = None
    name: str | None = None
    deleted: str = "false"
    category_id: str | None = None
    sort_by: IndexSortByType | None = "name"
    sort_desc: bool | None = False


class RepositoryPaginatedIndexRequest(RepositoryIndexRequest):
    page: int = 1
    page_size: int = 10


class RepositoriesByCategory(BaseModel):
    id: str
    name: str
    description: str
    repository_count: int
    repositories: list[Repository]


class RepositoryIndexResponse(RootModel):
    root: list[Repository]


class RepositorySearchRequest(BaseModel):
    q: str
    page: int | None = None
    page_size: int | None = None


class RepositorySearchResult(BaseModel):
    id: str
    name: str
    repo_owner_username: str
    description: str
    long_description: str | None = None
    remote_repository_url: str | None = None
    homepage_url: str | None = None
    last_update: str | None = None
    full_last_updated: str
    repo_lineage: str
    approved: bool
    times_downloaded: int
    categories: str


class RepositorySearchHit(BaseModel):
    score: float
    repository: RepositorySearchResult


class RepositorySearchResults(BaseModel):
    total_results: str
    page: str
    page_size: str
    hostname: str
    hits: list[RepositorySearchHit]


# align with the search version of this to some degree but fix some things also
class PaginatedRepositoryIndexResults(BaseModel):
    total_results: int
    page: int
    page_size: int
    hostname: str
    hits: list[Repository]


class GetInstallInfoRequest(BaseModel):
    owner: str
    name: str
    changeset_revision: str


class ValidToolDict(TypedDict):
    add_to_tool_panel: bool
    description: str
    guid: str
    id: str
    name: str
    requirements: list
    tests: list
    tool_config: str
    tool_type: str
    version: str
    version_string_cmd: str | None


class RepositoryMetadataInstallInfoDict(TypedDict):
    changeset_revision: str
    downloadable: bool
    has_repository_dependencies: bool
    has_repository_dependencies_only_if_compiling_contained_td: bool
    id: str
    includes_datatypes: bool
    includes_tool_dependencies: bool
    includes_tools: bool
    includes_tools_for_display_in_tool_panel: bool
    includes_workflows: bool
    malicious: bool
    repository_id: str
    url: str
    valid_tools: list[ValidToolDict]


# So hard to type this... the keys are repo names and the elements
# are tuples that have been list-ified.
ExtraRepoInfo = dict[str, list]
# {
#     "add_column": [
#         "add_column hello",
#         "http://test@localhost:9009/repos/test/add_column",
#         "3a08cc21466f",
#         "1",
#         "test",
#         {},
#         {}
#     ]
# }


class EmptyDict(TypedDict):
    pass


LegacyInstallInfoTuple = tuple[dict | None, RepositoryMetadataInstallInfoDict | EmptyDict, ExtraRepoInfo | EmptyDict]


class RepositoryExtraInstallInfo(BaseModel):
    name: str
    description: str
    repository_clone_url: str
    changeset_revision: str
    ctx_rev: str
    repository_owner: str
    repository_dependencies: dict | None = None
    # tool dependencies not longer work so don't transmit them in v2?
    # tool_dependencies: Optional[Dict]

    @staticmethod
    def from_legacy_dict(as_dict: ExtraRepoInfo) -> "RepositoryExtraInstallInfo":
        assert len(as_dict) == 1
        repo_name = next(iter(as_dict.keys()))
        info_indexable = as_dict[repo_name]
        return RepositoryExtraInstallInfo(
            name=repo_name,
            description=info_indexable[0],
            repository_clone_url=info_indexable[1],
            changeset_revision=info_indexable[2],
            ctx_rev=info_indexable[3],
            repository_owner=info_indexable[4],
            repository_dependencies=info_indexable[5],
        )


class ValidTool(BaseModel):
    add_to_tool_panel: bool
    description: str
    guid: str
    id: str
    name: str
    requirements: list
    tests: list
    tool_config: str
    tool_type: str
    version: str
    version_string_cmd: str | None = None

    @staticmethod
    def from_legacy_dict(as_dict: ValidToolDict) -> "ValidTool":
        return ValidTool(**as_dict)

    @staticmethod
    def from_legacy_list(as_dicts: list[ValidToolDict]) -> list["ValidTool"]:
        return [ValidTool.from_legacy_dict(d) for d in as_dicts]


class RepositoryMetadataInstallInfo(BaseModel):
    id: str
    changeset_revision: str
    downloadable: bool
    has_repository_dependencies: bool
    includes_tools: bool
    includes_tools_for_display_in_tool_panel: bool
    malicious: bool
    repository_id: str
    url: str
    valid_tools: list[ValidTool]
    # no longer used, don't transmit.
    # has_repository_dependencies_only_if_compiling_contained_td: bool
    # includes_datatypes: bool
    # includes_tool_dependencies: bool
    # includes_workflows: bool

    @staticmethod
    def from_legacy_dict(as_dict: RepositoryMetadataInstallInfoDict) -> "RepositoryMetadataInstallInfo":
        return RepositoryMetadataInstallInfo(
            id=as_dict["id"],
            changeset_revision=as_dict["changeset_revision"],
            downloadable=as_dict["downloadable"],
            has_repository_dependencies=as_dict["has_repository_dependencies"],
            includes_tools=as_dict["includes_tools"],
            includes_tools_for_display_in_tool_panel=as_dict["includes_tools_for_display_in_tool_panel"],
            malicious=as_dict["malicious"],
            repository_id=as_dict["repository_id"],
            url=as_dict["url"],
            valid_tools=ValidTool.from_legacy_list(as_dict.get("valid_tools", [])),
        )


class InstallInfo(BaseModel):
    metadata_info: RepositoryMetadataInstallInfo | None = None
    repo_info: RepositoryExtraInstallInfo | None = None


def from_legacy_install_info(legacy_install_info: LegacyInstallInfoTuple) -> InstallInfo:
    repo_metadata_install_info: RepositoryMetadataInstallInfoDict | EmptyDict
    extra_info: ExtraRepoInfo | EmptyDict
    _, repo_metadata_install_info, extra_info = legacy_install_info
    if repo_metadata_install_info:
        metadata_info = RepositoryMetadataInstallInfo.from_legacy_dict(repo_metadata_install_info)
    else:
        metadata_info = None
    if extra_info:
        repo_info = RepositoryExtraInstallInfo.from_legacy_dict(extra_info)
    else:
        repo_info = None
    return InstallInfo(
        metadata_info=metadata_info,
        repo_info=repo_info,
    )


class BuildSearchIndexResponse(BaseModel):
    repositories_indexed: int
    tools_indexed: int


class Version(BaseModel):
    version_major: str
    version: str
    api_version: str = "v1"


class ShedParsedTool(ParsedTool):
    repository_revision: RepositoryRevisionMetadata | None = None

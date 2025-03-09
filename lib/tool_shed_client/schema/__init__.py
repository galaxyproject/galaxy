from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)
from typing_extensions import (
    Literal,
    TypedDict,
)


class Repository(BaseModel):
    # element/collection view on the backend have same keys/impl
    id: str
    name: str
    owner: str
    type: str  # TODO: enum
    remote_repository_url: Optional[str] = None
    homepage_url: Optional[str] = None
    description: str
    user_id: str
    private: bool
    deleted: bool
    times_downloaded: int
    deprecated: bool
    create_time: str
    update_time: str


class DetailedRepository(Repository):
    long_description: Optional[str]


class RepositoryPermissions(BaseModel):
    allow_push: List[str]
    can_manage: bool  # can the requesting user manage the repository
    can_push: bool


class RepositoryRevisionReadmes(RootModel):
    root: Dict[str, str]


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
    description: Optional[str] = None


class ValidRepostiroyUpdateMessage(BaseModel):
    message: str


class FailedRepositoryUpdateMessage(BaseModel):
    err_msg: str


class GetOrderedInstallableRevisionsRequest(BaseModel):
    name: str
    owner: str


class OrderedInstallableRevisions(RootModel):
    root: List[str]


RepositoryType = Literal[
    "repository_suite_definition",
    "tool_dependency_definition",
    "unrestricted",
]


class CreateRepositoryRequest(BaseModel):
    name: str
    synopsis: str
    description: Optional[str] = None
    remote_repository_url: Optional[str] = None
    homepage_url: Optional[str] = None
    type_: RepositoryType = Field(
        "unrestricted",
        alias="type",
        title="Type",
    )
    category_ids: Optional[Union[List[str], str]] = Field(
        ...,
        alias="category_ids[]",
        title="Category IDs",
    )
    model_config = ConfigDict(populate_by_name=True)


class UpdateRepositoryRequest(BaseModel):
    name: Optional[str] = None
    synopsis: Optional[str] = None
    type_: Optional[RepositoryType] = Field(
        None,
        alias="type",
        title="Type",
    )
    description: Optional[str] = None
    remote_repository_url: Optional[str] = None
    homepage_url: Optional[str] = None
    category_ids: Optional[List[str]] = Field(
        None,
        alias="category_ids",
        title="Category IDs",
    )
    model_config = ConfigDict(populate_by_name=True)


class RepositoryUpdateRequest(BaseModel):
    commit_message: Optional[str] = None


class RepositoryUpdate(RootModel):
    root: Union[ValidRepostiroyUpdateMessage, FailedRepositoryUpdateMessage]

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


class RepositoryRevisionMetadata(BaseModel):
    id: str
    repository: Repository
    repository_dependencies: List["RepositoryDependency"]
    tools: Optional[List["RepositoryTool"]] = None
    invalid_tools: List[str]  # added for rendering list of invalid tools in 2.0 frontend
    repository_id: str
    numeric_revision: int
    changeset_revision: str
    malicious: bool
    downloadable: bool
    missing_test_components: bool
    has_repository_dependencies: bool
    includes_tools: bool
    includes_tools_for_display_in_tool_panel: bool
    # Deprecate these...
    includes_tool_dependencies: Optional[bool] = None
    includes_datatypes: Optional[bool] = None
    includes_workflows: Optional[bool] = None


class RepositoryDependency(RepositoryRevisionMetadata):
    # This only needs properties for tests it seems?
    # e.g. test_0550_metadata_updated_dependencies.py
    pass


class RepositoryMetadata(RootModel):
    root: Dict[str, RepositoryRevisionMetadata]

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


class ResetMetadataOnRepositoryRequest(BaseModel):
    repository_id: str


class ResetMetadataOnRepositoryResponse(BaseModel):
    status: str  # TODO: enum...
    repository_status: List[str]
    start_time: str
    stop_time: str


# Ugh - use with care - param descriptions scraped from older version of the API.
class ResetMetadataOnRepositoriesRequest(BaseModel):
    my_writable: bool = Field(
        False,
        description="""if the API key is associated with an admin user in the Tool Shed, setting this param value
to True will restrict resetting metadata to only repositories that are writable by the user
in addition to those repositories of type tool_dependency_definition.  This param is ignored
if the current user is not an admin user, in which case this same restriction is automatic.""",
    )
    encoded_ids_to_skip: Optional[List[str]] = Field(
        None, description="a list of encoded repository ids for repositories that should not be processed"
    )


class ResetMetadataOnRepositoriesResponse(BaseModel):
    repository_status: List[str]
    start_time: str
    stop_time: str


class ToolSearchRequest(BaseModel):
    q: str
    page: Optional[int] = None
    page_size: Optional[int] = None


class ToolSearchHitTool(BaseModel):
    id: str
    repo_owner_username: str
    repo_name: str
    name: str
    description: str


class ToolSearchHit(BaseModel):
    tool: ToolSearchHitTool
    matched_terms: Dict[str, Any]
    score: float


class ToolSearchResults(BaseModel):
    # These next three really should be ints :<
    total_results: str
    page: str
    page_size: str
    hostname: str
    hits: List[ToolSearchHit]

    def find_search_hit(self, repository: Repository) -> Optional[ToolSearchHit]:
        matching_hit: Optional[ToolSearchHit] = None

        for hit in self.hits:
            owner_matches = hit.tool.repo_owner_username == repository.owner
            name_matches = hit.tool.repo_name == repository.name
            if owner_matches and name_matches:
                matching_hit = hit
                break

        return matching_hit


IndexSortByType = Literal["name", "create_time"]


class RepositoryIndexRequest(BaseModel):
    filter: Optional[str] = None
    owner: Optional[str] = None
    name: Optional[str] = None
    deleted: str = "false"
    category_id: Optional[str] = None
    sort_by: Optional[IndexSortByType] = "name"
    sort_desc: Optional[bool] = False


class RepositoryPaginatedIndexRequest(RepositoryIndexRequest):
    page: int = 1
    page_size: int = 10


class RepositoriesByCategory(BaseModel):
    id: str
    name: str
    description: str
    repository_count: int
    repositories: List[Repository]


class RepositoryIndexResponse(RootModel):
    root: List[Repository]


class RepositorySearchRequest(BaseModel):
    q: str
    page: Optional[int] = None
    page_size: Optional[int] = None


class RepositorySearchResult(BaseModel):
    id: str
    name: str
    repo_owner_username: str
    description: str
    long_description: Optional[str] = None
    remote_repository_url: Optional[str] = None
    homepage_url: Optional[str] = None
    last_update: Optional[str] = None
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
    hits: List[RepositorySearchHit]


# align with the search version of this to some degree but fix some things also
class PaginatedRepositoryIndexResults(BaseModel):
    total_results: int
    page: int
    page_size: int
    hostname: str
    hits: List[Repository]


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
    version_string_cmd: Optional[str]


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
    valid_tools: List[ValidToolDict]


# So hard to type this... the keys are repo names and the elements
# are tuples that have been list-ified.
ExtraRepoInfo = Dict[str, List]
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


LegacyInstallInfoTuple = Tuple[
    Optional[Dict], Union[RepositoryMetadataInstallInfoDict, EmptyDict], Union[ExtraRepoInfo, EmptyDict]
]


class RepositoryExtraInstallInfo(BaseModel):
    name: str
    description: str
    repository_clone_url: str
    changeset_revision: str
    ctx_rev: str
    repository_owner: str
    repository_dependencies: Optional[Dict] = None
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
    version_string_cmd: Optional[str] = None

    @staticmethod
    def from_legacy_dict(as_dict: ValidToolDict) -> "ValidTool":
        return ValidTool(**as_dict)

    @staticmethod
    def from_legacy_list(as_dicts: List[ValidToolDict]) -> List["ValidTool"]:
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
    valid_tools: List[ValidTool]
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
    metadata_info: Optional[RepositoryMetadataInstallInfo] = None
    repo_info: Optional[RepositoryExtraInstallInfo] = None


def from_legacy_install_info(legacy_install_info: LegacyInstallInfoTuple) -> InstallInfo:
    repo_metadata_install_info: Union[RepositoryMetadataInstallInfoDict, EmptyDict]
    extra_info: Union[ExtraRepoInfo, EmptyDict]
    _, repo_metadata_install_info, extra_info = legacy_install_info
    if repo_metadata_install_info:
        metadata_info = RepositoryMetadataInstallInfo.from_legacy_dict(
            cast(RepositoryMetadataInstallInfoDict, repo_metadata_install_info)
        )
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

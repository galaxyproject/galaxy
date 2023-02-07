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
    Field,
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
    remote_repository_url: Optional[str]
    homepage_url: Optional[str]
    description: str
    user_id: str
    private: bool
    deleted: bool
    times_downloaded: int
    deprecated: bool
    create_time: str


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str


class User(BaseModel):
    id: str
    username: str


class Category(BaseModel):
    id: str
    name: str


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


class OrderedInstallableRevisions(BaseModel):
    __root__: List[str]


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
    category_ids: str = Field(
        ...,
        alias="category_ids[]",
        title="Category IDs",
    )

    class Config:
        allow_population_by_field_name = True


class RepositoryUpdateRequest(BaseModel):
    commit_message: Optional[str] = None


class RepositoryUpdate(BaseModel):
    __root__: Union[ValidRepostiroyUpdateMessage, FailedRepositoryUpdateMessage]

    @property
    def is_ok(self):
        return isinstance(self.__root__, ValidRepostiroyUpdateMessage)


class RepositoryDependency(BaseModel):
    pass


class RepositoryTool(BaseModel):
    pass


class RepositoryRevisionMetadata(BaseModel):
    id: str
    repository: Repository
    repository_dependencies: List[RepositoryDependency]
    tools: Optional[List[RepositoryTool]]
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
    includes_tool_dependencies: Optional[bool]
    includes_datatypes: Optional[bool]
    includes_workflows: Optional[bool]


class RepositoryMetadata(BaseModel):
    __root__: Dict[str, RepositoryRevisionMetadata]

    @property
    def latest_revision(self) -> RepositoryRevisionMetadata:
        return list(self.__root__.values())[-1]

    @property
    def tip(self) -> str:
        if self.is_new:
            return "000000000000"
        else:
            return self.latest_revision.changeset_revision

    @property
    def is_new(self) -> bool:
        return len(self.__root__) == 0


class ResetMetadataOnRepositoryRequest(BaseModel):
    repository_id: str


class ResetMetadataOnRepositoryResponse(BaseModel):
    status: str  # TODO: enum...
    repository_status: List[str]
    start_time: str
    stop_time: str


class ToolSearchRequest(BaseModel):
    q: str
    page: Optional[int]
    page_size: Optional[int]


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


class RepositoryIndexRequest(BaseModel):
    owner: Optional[str]
    name: Optional[str]
    deleted: str = "false"


class RepositoryIndexResponse(BaseModel):
    __root__: List[Repository]


class RepositorySearchRequest(BaseModel):
    q: str
    page: Optional[int]
    page_size: Optional[int]


class RepositorySearchResult(BaseModel):
    id: str
    name: str
    repo_owner_username: str
    description: str
    long_description: Optional[str]
    remote_repository_url: Optional[str]
    homepage_url: Optional[str]
    last_update: Optional[str]
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

EmptyDict = TypedDict("EmptyDict", {})
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
    repository_dependencies: Optional[Dict]
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
    version_string_cmd: Optional[str]

    @staticmethod
    def from_legacy_dict(as_dict: ValidToolDict) -> "ValidTool":
        return ValidTool(**as_dict)

    @staticmethod
    def from_legacy_list(as_dicts: List[ValidToolDict]) -> List["ValidTool"]:
        return list(ValidTool.from_legacy_dict(d) for d in as_dicts)


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
    valid_tools: List[ValidToolDict]
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
            valid_tools=ValidTool.from_legacy_list(as_dict["valid_tools"]),
        )


class InstallInfo(BaseModel):
    metadata_info: Optional[RepositoryMetadataInstallInfo]
    repo_info: Optional[RepositoryExtraInstallInfo]


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

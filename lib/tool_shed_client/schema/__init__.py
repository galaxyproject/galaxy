from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import BaseModel


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


class Category(BaseModel):
    id: str
    name: str


class CreateCategoryRequest(BaseModel):
    name: str
    description: str


class ValidRepostiroyUpdateMessage(BaseModel):
    message: str


class FailedRepositoryUpdateMessage(BaseModel):
    err_msg: str


class GetOrderedInstallableRevisionsRequest(BaseModel):
    name: str
    owner: str


class OrderedInstallableRevisions(BaseModel):
    __root__: List[str]


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
    tools: List[RepositoryTool]
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

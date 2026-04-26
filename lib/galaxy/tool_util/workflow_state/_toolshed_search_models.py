"""Pydantic models for Tool Shed search and repository search wire payloads.

Mirrors the TypeScript ``@galaxy-tool-util/search`` models. Wire fields stay
snake_case to match the Tool Shed JSON; downstream code (``tool_search``)
flattens these into camelCase-equivalent ``NormalizedToolHit`` objects.

Pagination integers (``total_results``, ``page``, ``page_size``) come back from
the Tool Shed as either numbers or numeric strings — a ``BeforeValidator``
coerces both shapes.
"""

from typing import (
    Annotated,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
)

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
)


def _coerce_count(value: object) -> object:
    if isinstance(value, bool):  # bool is an int subclass — guard explicitly
        raise ValueError("must be a number or numeric string")
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return float(value)
    raise ValueError("must be a number or numeric string")


CoercedCount = Annotated[int, BeforeValidator(_coerce_count)]


class ToolSearchHitTool(BaseModel):
    """Inner ``tool`` block of a Tool Shed tool search hit."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    description: Optional[str] = None
    repo_name: str
    repo_owner_username: str
    version: Optional[str] = None
    changeset_revision: Optional[str] = None


class ToolSearchHit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tool: ToolSearchHitTool
    matched_terms: Dict[str, str] = Field(default_factory=dict)
    score: float


class RepositorySearchHitRepo(BaseModel):
    """Inner ``repository`` block of a Tool Shed repo search hit."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    repo_owner_username: str
    description: Optional[str] = None
    long_description: Optional[str] = None
    remote_repository_url: Optional[str] = None
    homepage_url: Optional[str] = None
    last_update: Optional[str] = None
    full_last_updated: Optional[str] = None
    categories: Optional[str] = None
    approved: bool
    times_downloaded: CoercedCount


class RepositorySearchHit(BaseModel):
    model_config = ConfigDict(extra="ignore")

    repository: RepositorySearchHitRepo
    score: float


HitT = TypeVar("HitT", bound=BaseModel)


class SearchResults(BaseModel, Generic[HitT]):
    model_config = ConfigDict(extra="ignore")

    total_results: CoercedCount
    page: CoercedCount
    page_size: CoercedCount
    hostname: str
    hits: List[HitT]


class TRSToolVersion(BaseModel):
    """Subset of a TRS ``ToolVersion`` we consume; extras allowed."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: Optional[str] = None
    url: str
    descriptor_type: List[str]
    author: List[str]


class ToolRevisionMatch(BaseModel):
    """A changeset revision that publishes a particular tool id."""

    changeset_revision: str
    tool_version: str
    order: int

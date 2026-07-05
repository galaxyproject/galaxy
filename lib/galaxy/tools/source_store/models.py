"""
Pydantic models for Tool Source Store API serialization.
"""

from datetime import datetime
from typing import (
    Any,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ToolSourceResponse(BaseModel):
    """Response model for tool source metadata."""

    model_config = ConfigDict(from_attributes=True)

    hash: str = Field(description="Content hash (SHA256)")
    tool_source_class: str = Field(description="Tool source class name")
    tool_id: str | None = Field(None, description="Tool ID")
    tool_version: str | None = Field(None, description="Tool version")
    tool_dir: str | None = Field(None, description="Tool directory")
    stored_at: datetime | None = Field(None, description="Storage timestamp")


class ToolSourceDetailResponse(ToolSourceResponse):
    """Detailed response model including raw source."""

    raw_source: str = Field(description="Raw tool source content")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ToolSourceListResponse(BaseModel):
    """Response model for listing tool sources."""

    total_count: int = Field(description="Total number of tool sources")
    items: list[ToolSourceResponse] = Field(description="List of tool sources")


class ToolSourceStatsResponse(BaseModel):
    """Response model for tool source storage statistics."""

    backend: str = Field(description="Storage backend type")
    count: int = Field(description="Number of stored tool sources")
    size_bytes: int | None = Field(None, description="Total storage size in bytes")


class ToolIndexEntryResponse(BaseModel):
    """Response model for tool index entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Tool ID")
    uuid: str | None = Field(None, description="Tool UUID")
    version: str | None = Field(None, description="Tool version")
    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    panel_section_id: str | None = Field(None, description="Panel section ID")
    panel_section_name: str | None = Field(None, description="Panel section name")
    labels: list[str] = Field(default_factory=list, description="Tool labels")
    edam_operations: list[str] = Field(default_factory=list, description="EDAM operations")
    edam_topics: list[str] = Field(default_factory=list, description="EDAM topics")
    hidden: bool = Field(False, description="Whether tool is hidden")
    test_count: int = Field(0, description="Number of tests")


class ToolIndexStatsResponse(BaseModel):
    """Response model for tool index statistics."""

    index_size: int = Field(description="Number of tools in index")
    memory_estimate_bytes: int = Field(description="Estimated memory usage")
    version: str = Field(description="Index version")
    built_at: datetime | None = Field(None, description="Index build timestamp")


class TestsSummaryResponse(BaseModel):
    """Response model for /api/tools/tests_summary."""

    # Dict of tool_id -> version -> {tool_name, count}
    # Using Dict[str, Any] because nested structure
    model_config = ConfigDict(extra="allow")


class RequirementResponse(BaseModel):
    """Response model for a tool requirement."""

    name: str = Field(description="Requirement name")
    version: str | None = Field(None, description="Requirement version")
    type: str = Field("package", description="Requirement type")


class SanitizeAllowlistResponse(BaseModel):
    """Response model for /api/sanitize_allow."""

    blocked_toolshed: list[dict[str, Any]] = Field(default_factory=list, description="Blocked tool shed tools")
    allowed_toolshed: list[dict[str, Any]] = Field(default_factory=list, description="Allowed tool shed tools")
    blocked_local: list[dict[str, Any]] = Field(default_factory=list, description="Blocked local tools")
    allowed_local: list[dict[str, Any]] = Field(default_factory=list, description="Allowed local tools")


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""

    tool_cache_size: int = Field(description="Number of cached Tool objects")
    tool_cache_maxsize: int = Field(description="Maximum cache size")
    index_size: int = Field(description="Number of tools in index")
    index_memory_estimate: int = Field(description="Estimated index memory usage")


class ToolIndexEntryListResponse(BaseModel):
    """Response model for paginated tool index entry listings."""

    total_count: int = Field(description="Total number of index entries")
    items: list[ToolIndexEntryResponse] = Field(description="List of index entries")


class ClearCacheResponse(BaseModel):
    """Response model for cache clear operation."""

    status: str = Field(description="Operation status")

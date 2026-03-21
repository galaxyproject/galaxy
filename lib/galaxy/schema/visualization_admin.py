from typing import Optional

from pydantic import (
    Field,
    RootModel,
)

from galaxy.schema.schema import Model


class VisualizationPackageMetadata(Model):
    description: Optional[str] = Field(None, title="Description")
    author: Optional[str] = Field(None, title="Author")
    license: Optional[str] = Field(None, title="License")
    dependencies: Optional[dict[str, str]] = Field(None, title="Dependencies")
    homepage: Optional[str] = Field(None, title="Homepage")


class InstalledVisualizationResponse(Model):
    id: str = Field(..., title="ID", description="The visualization identifier.")
    package: str = Field(..., title="Package", description="The npm package name.")
    version: str = Field(..., title="Version", description="The installed package version.")
    enabled: bool = Field(..., title="Enabled", description="Whether this visualization is enabled.")
    installed: bool = Field(..., title="Installed", description="Whether files are present on disk.")
    path: Optional[str] = Field(None, title="Path", description="Filesystem path to the installed package.")
    size: Optional[int] = Field(None, title="Size", description="Total size in bytes.")
    metadata: Optional[dict] = Field(None, title="Metadata", description="Package metadata from package.json.")
    message: Optional[str] = Field(None, title="Message", description="Status message.")


class InstalledVisualizationListResponse(RootModel):
    root: list[InstalledVisualizationResponse]


class AvailableVisualizationResponse(Model):
    name: str = Field(..., title="Name", description="The npm package name.")
    description: str = Field("", title="Description", description="Package description.")
    version: str = Field("", title="Version", description="Latest published version.")
    keywords: list[str] = Field(default_factory=list, title="Keywords")
    author: Optional[dict] = Field(None, title="Author")
    maintainers: list[dict] = Field(default_factory=list, title="Maintainers")
    links: Optional[dict] = Field(None, title="Links", description="Homepage, repository, etc.")
    date: Optional[str] = Field(None, title="Date", description="Last publish date.")
    score: Optional[dict] = Field(None, title="Score", description="NPM search score.")


class AvailableVisualizationListResponse(RootModel):
    root: list[AvailableVisualizationResponse]


class InstallVisualizationRequest(Model):
    package: str = Field(..., title="Package", description="The npm package name to install.")
    version: str = Field(..., title="Version", description="The package version to install.")


class UpdateVisualizationRequest(Model):
    version: str = Field(..., title="Version", description="The new version to update to.")


class ToggleVisualizationRequest(Model):
    enabled: bool = Field(
        ...,
        title="Enabled",
        description="Whether to enable or disable the visualization.",
    )


class ToggleVisualizationResponse(Model):
    id: str = Field(..., title="ID")
    enabled: bool = Field(..., title="Enabled")
    message: str = Field(..., title="Message")


class MessageResponse(Model):
    message: str = Field(..., title="Message")


class StagingResultResponse(Model):
    message: str = Field(..., title="Message")
    staged_count: int = Field(..., title="Staged Count")
    staged_visualizations: list[str] = Field(default_factory=list, title="Staged Visualizations")
    errors: list[str] = Field(default_factory=list, title="Errors")


class VisualizationStagingResultResponse(Model):
    message: str = Field(..., title="Message")
    visualization_id: str = Field(..., title="Visualization ID")
    source_path: str = Field(..., title="Source Path")
    target_path: str = Field(..., title="Target Path")
    size: int = Field(0, title="Size")


class CleanStagingResultResponse(Model):
    message: str = Field(..., title="Message")
    cleaned_count: int = Field(..., title="Cleaned Count")
    cleaned_items: list[str] = Field(default_factory=list, title="Cleaned Items")


class StagedVisualizationInfo(Model):
    name: str = Field(..., title="Name")
    path: str = Field(..., title="Path")
    size: int = Field(..., title="Size")
    last_modified: float = Field(..., title="Last Modified")


class StagingStatusResponse(Model):
    message: str = Field(..., title="Message")
    staged_count: int = Field(..., title="Staged Count")
    staged_visualizations: list[StagedVisualizationInfo] = Field(default_factory=list, title="Staged Visualizations")
    total_size: int = Field(0, title="Total Size")


class PackageVersionsResponse(Model):
    package: str = Field(..., title="Package", description="The npm package name.")
    versions: list[str] = Field(
        default_factory=list,
        title="Versions",
        description="Available versions, newest first.",
    )


class UsageStatsResponse(Model):
    message: str = Field(..., title="Message")
    days: int = Field(..., title="Days")
    stats: dict = Field(default_factory=dict, title="Stats")

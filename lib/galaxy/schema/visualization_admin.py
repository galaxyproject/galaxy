from typing import (
    Any,
)

from pydantic import (
    Field,
    RootModel,
)

from galaxy.schema.schema import Model


class VisualizationPackageMetadata(Model):
    description: str | None = Field(None, title="Description")
    author: str | None = Field(None, title="Author")
    license: str | None = Field(None, title="License")
    dependencies: dict[str, str] | None = Field(None, title="Dependencies")
    homepage: str | None = Field(None, title="Homepage")


class InstalledVisualizationResponse(Model):
    id: str = Field(..., title="ID", description="The visualization identifier.")
    package: str = Field(..., title="Package", description="The npm package name.")
    version: str = Field(..., title="Version", description="The installed package version.")
    enabled: bool = Field(..., title="Enabled", description="Whether this visualization is enabled.")
    installed: bool = Field(..., title="Installed", description="Whether files are present on disk.")
    path: str | None = Field(None, title="Path", description="Filesystem path to the installed package.")
    size: int | None = Field(None, title="Size", description="Total size in bytes.")
    metadata: dict[str, Any] | None = Field(None, title="Metadata", description="Package metadata from package.json.")
    message: str | None = Field(None, title="Message", description="Status message.")


class InstalledVisualizationListResponse(RootModel[list[InstalledVisualizationResponse]]):
    root: list[InstalledVisualizationResponse]


class AvailableVisualizationResponse(Model):
    name: str = Field(..., title="Name", description="The npm package name.")
    description: str = Field("", title="Description", description="Package description.")
    version: str = Field("", title="Version", description="Latest published version.")
    keywords: list[str] = Field(default_factory=list, title="Keywords")
    author: dict[str, Any] | None = Field(None, title="Author")
    maintainers: list[dict[str, Any]] = Field(default_factory=list, title="Maintainers")
    links: dict[str, Any] | None = Field(None, title="Links", description="Homepage, repository, etc.")
    date: str | None = Field(None, title="Date", description="Last publish date.")
    score: dict[str, Any] | None = Field(None, title="Score", description="NPM search score.")


class AvailableVisualizationListResponse(RootModel[list[AvailableVisualizationResponse]]):
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


class PackageVersionsResponse(Model):
    package: str = Field(..., title="Package", description="The npm package name.")
    versions: list[str] = Field(
        default_factory=list,
        title="Versions",
        description="Available versions, newest first.",
    )

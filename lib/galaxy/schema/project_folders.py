"""Schemas for project folders, an optional per-user grouping of histories."""

from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import Model

FolderNameField = Field(
    ...,
    title="Name",
    description="The name of the project folder.",
    min_length=1,
    max_length=255,
)


class ProjectFolderSummary(Model):
    """A project folder and how many histories are filed under it."""

    id: EncodedDatabaseIdField = Field(..., title="ID", description="Encoded ID of the project folder.")
    name: str = FolderNameField
    create_time: datetime = Field(..., title="Create Time", description="When this folder was created.")
    update_time: datetime = Field(..., title="Update Time", description="When this folder was last changed.")
    count: int = Field(
        ...,
        title="Count",
        description="Number of the user's histories filed under this folder. Excludes deleted histories.",
    )


class CreateProjectFolderPayload(BaseModel):
    name: str = FolderNameField


class UpdateProjectFolderPayload(BaseModel):
    name: str = FolderNameField


class SetHistoryProjectFolderPayload(BaseModel):
    project_folder_id: EncodedDatabaseIdField | None = Field(
        None,
        title="Project Folder ID",
        description="Folder to file the history under, or null to leave it unfiled.",
    )

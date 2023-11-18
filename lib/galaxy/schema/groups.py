from typing import List

from pydantic import (
    Field,
    Required,
)

from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import Model


class GroupIndexResponse(Model):
    """Response schema for a group."""

    model_class: str = Field(
        Required,
        title="model class",
        description="model class",
    )
    id: EncodedDatabaseIdField = Field(
        Required,
        title="group ID",
        description="Encoded group ID",
    )
    url: str = Field(
        Required,
        title="URL for the group",
        description="URL for the group",
    )
    name: str = Field(
        Required,
        title="name of the group",
        description="name of the group",
    )


class GroupIndexListResponse(Model):
    """Response schema for listing groups."""

    __root__: List[GroupIndexResponse]


class GroupShowResponse(Model):
    """Response schema for showing a group."""

    model_class: str = Field(
        Required,
        title="model class",
        description="model class",
    )
    id: str = Field(
        Required,
        title="group ID",
        description="Encoded group ID",
    )
    url: str = Field(
        Required,
        title="URL for the group",
        description="URL for the group",
    )
    name: str = Field(
        Required,
        title="name of the group",
        description="name of the group",
    )
    roles_url: str = Field(
        Required,
        title="URL for the roles of the group",
        description="URL for the roles of the group",
    )
    users_url: str = Field(
        Required,
        title="URL for the users of the group",
        description="URL for the users of the group",
    )


class GroupCreatePayload(Model):
    """Payload schema for creating a group."""

    name: str = Field(
        Required,
        title="name of the group",
        description="name of the group",
    )
    user_ids: List[EncodedDatabaseIdField] = Field(
        [],
        title="user IDs",
        description="Encoded user IDs",
    )
    role_ids: List[EncodedDatabaseIdField] = Field(
        [],
        title="role IDs",
        description="Encoded role IDs",
    )

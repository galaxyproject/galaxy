from typing import List

from pydantic import Field
from typing_extensions import Literal

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    ModelClassField,
)
from galaxy.schema.schema import Model

GROUP_MODEL_CLASS = Literal["Group"]


class GroupIndexResponse(Model):
    """Response schema for a group."""

    model_class: GROUP_MODEL_CLASS = ModelClassField(GROUP_MODEL_CLASS)
    id: DecodedDatabaseIdField = Field(
        ...,
        title="group ID",
    )
    url: str = Field(
        ...,
        title="URL for the group",
    )
    name: str = Field(
        ...,
        title="name of the group",
    )


class GroupIndexListResponse(Model):
    """Response schema for listing groups."""

    __root__: List[GroupIndexResponse]


class GroupShowResponse(Model):
    """Response schema for showing a group."""

    model_class: GROUP_MODEL_CLASS = ModelClassField(GROUP_MODEL_CLASS)
    id: str = Field(
        ...,
        title="group ID",
    )
    url: str = Field(
        ...,
        title="URL for the group",
    )
    name: str = Field(
        ...,
        title="name of the group",
    )
    roles_url: str = Field(
        ...,
        title="URL for the roles of the group",
    )
    users_url: str = Field(
        ...,
        title="URL for the users of the group",
    )


class GroupCreatePayload(Model):
    """Payload schema for creating a group."""

    name: str = Field(
        ...,
        title="name of the group",
        description="name of the group",
    )
    user_ids: List[DecodedDatabaseIdField] = Field(
        [],
        title="user IDs",
    )
    role_ids: List[DecodedDatabaseIdField] = Field(
        [],
        title="role IDs",
    )

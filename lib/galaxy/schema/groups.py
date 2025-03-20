from typing import (
    List,
    Optional,
)

from pydantic import (
    Field,
    RootModel,
)
from typing_extensions import Literal

from galaxy.schema import partial_model
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
    ModelClassField,
)
from galaxy.schema.schema import (
    Model,
    WithModelClass,
)

GROUP_MODEL_CLASS = Literal["Group"]


class GroupResponse(Model, WithModelClass):
    """Response schema for a group."""

    model_class: GROUP_MODEL_CLASS = ModelClassField(GROUP_MODEL_CLASS)
    id: EncodedDatabaseIdField = Field(
        ...,
        title="group ID",
    )
    name: str = Field(
        ...,
        title="name of the group",
    )
    url: str = Field(
        ...,
        title="URL for the group",
    )
    roles_url: Optional[str] = Field(
        None,
        title="URL for the roles of the group",
    )
    users_url: Optional[str] = Field(
        None,
        title="URL for the users of the group",
    )


class GroupListResponse(RootModel):
    """Response schema for listing groups."""

    root: List[GroupResponse]


class GroupCreatePayload(Model):
    """Payload schema for creating a group."""

    name: str = Field(
        ...,
        title="name of the group",
    )
    user_ids: List[DecodedDatabaseIdField] = Field(
        [],
        title="user IDs",
    )
    role_ids: List[DecodedDatabaseIdField] = Field(
        [],
        title="role IDs",
    )


@partial_model()
class GroupUpdatePayload(Model):
    """Payload schema for updating a group."""

    name: str = Field(
        ...,
        title="name of the group",
    )
    user_ids: Optional[List[DecodedDatabaseIdField]] = Field(
        None,
        title="user IDs",
    )
    role_ids: Optional[List[DecodedDatabaseIdField]] = Field(
        None,
        title="role IDs",
    )

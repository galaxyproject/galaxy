from typing import (
    List,
    Optional,
)

from pydantic import (
    Field,
    Required,
)
from typing_extensions import Literal

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
    ModelClassField,
)
from galaxy.schema.schema import Model

GROUP_MODEL_CLASS = Literal["Group"]


class GroupResponse(Model):
    """Response schema for a group."""

    model_class: GROUP_MODEL_CLASS = ModelClassField(GROUP_MODEL_CLASS)
    id: EncodedDatabaseIdField = Field(
        Required,
        title="group ID",
    )
    name: str = Field(
        Required,
        title="name of the group",
    )
    url: str = Field(
        Required,
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


class GroupListResponse(Model):
    """Response schema for listing groups."""

    __root__: List[GroupResponse]


class GroupCreatePayload(Model):
    """Payload schema for creating a group."""

    name: str = Field(
        Required,
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

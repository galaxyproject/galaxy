from typing import (
    List,
    Optional,
)

from pydantic import (
    Field,
    RootModel,
)

from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import Model


class ItemTagsResponse(Model):
    """Response schema for showing an item tag."""

    model_class: str = Field(
        ...,
        title="model class",
    )
    id: EncodedDatabaseIdField = Field(
        ...,
        title="item tag ID",
    )
    user_tname: str = Field(
        ...,
        title="name of the item tag",
    )
    user_value: Optional[str] = Field(
        None,
        title="value of the item tag",
    )


class ItemTagsListResponse(RootModel):
    """Response schema for listing item tags."""

    root: List[ItemTagsResponse]


class ItemTagsCreatePayload(Model):
    """Payload schema for creating an item tag."""

    value: Optional[str] = Field(
        None,
        title="value of the item tag",
    )

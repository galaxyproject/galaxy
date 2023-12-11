from typing import (
    List,
    Optional,
)

from pydantic import (
    Field,
    Required,
)

from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import Model


class ItemTagsResponse(Model):
    """Response schema for showing an item tag."""

    model_class: str = Field(
        Required,
        title="model class",
    )
    id: EncodedDatabaseIdField = Field(
        Required,
        title="item tag ID",
    )
    user_tname: str = Field(
        Required,
        title="name of the item tag",
    )
    user_value: Optional[str] = Field(
        None,
        title="value of the item tag",
    )


class ItemTagsListResponse(Model):
    """Response schema for listing item tags."""

    __root__: List[ItemTagsResponse]


class ItemTagsCreatePayload(Model):
    """Payload schema for creating an item tag."""

    value: Optional[str] = Field(
        None,
        title="value of the item tag",
    )

from datetime import datetime
from enum import Enum
from typing import (
    List,
    Union,
)

from pydantic import Field
from typing_extensions import Literal

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.schema import (
    Model,
    UpdateTimeField,
)


class CleanableItemsSummary(Model):
    total_size: int = Field(
        ...,
        title="Total Size",
        description="The total size in bytes that can be recovered by purging all the items.",
    )
    total_items: int = Field(
        ...,
        title="Total Items",
        description="The total number of items that could be purged.",
    )


StoredItemType = Union[Literal["history"], Literal["dataset"]]


class StoredItem(Model):
    id: EncodedDatabaseIdField
    name: str
    type: StoredItemType
    size: int
    update_time: datetime = UpdateTimeField


class StoredItemOrderBy(str, Enum):
    """Available options for sorting Stored Items results."""

    NAME_ASC = "name-asc"
    NAME_DSC = "name-dsc"
    SIZE_ASC = "size-asc"
    SIZE_DSC = "size-dsc"
    UPDATE_TIME_ASC = "update_time-asc"
    UPDATE_TIME_DSC = "update_time-dsc"


class StorageItemCleanupError(Model):
    item_id: EncodedDatabaseIdField
    error: str


class CleanupStorageItemsRequest(Model):
    item_ids: List[DecodedDatabaseIdField]


class StorageItemsCleanupResult(Model):
    total_item_count: int
    success_item_count: int
    total_free_bytes: int
    errors: List[StorageItemCleanupError]

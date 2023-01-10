from datetime import datetime
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


class DiscardedItemsSummary(Model):
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


StoredItemType = Union[Literal["history"], Literal["hda"]]


class StoredItem(Model):
    id: EncodedDatabaseIdField
    name: str
    type: StoredItemType
    size: int
    update_time: datetime = UpdateTimeField


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

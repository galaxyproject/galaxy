from enum import Enum
from typing import Optional

from pydantic import Field

from galaxy.managers.context import ProvidesUserContext
from galaxy.model.tags import GalaxyTagHandlerSession
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    Model,
    TagCollection,
)


class TaggableItemClass(Enum):
    History = "History"
    HistoryDatasetAssociation = "HistoryDatasetAssociation"
    HistoryDatasetCollectionAssociation = "HistoryDatasetCollectionAssociation"
    LibraryDatasetDatasetAssociation = "LibraryDatasetDatasetAssociation"
    Page = "Page"
    StoredWorkflow = "StoredWorkflow"
    Visualization = "Visualization"


class ItemTagsPayload(Model):
    item_id: DecodedDatabaseIdField = Field(
        ...,  # This field is required
        title="Item ID",
        description="The `encoded identifier` of the item whose tags will be updated.",
    )
    item_class: TaggableItemClass = Field(
        ...,  # This field is required
        title="Item class",
        description="The name of the class of the item that will be tagged.",
    )
    item_tags: Optional[TagCollection] = Field(
        default=None,
        title="Item tags",
        description="The list of tags that will replace the current tags associated with the item.",
    )


class TagsManager:
    """Interface/service object shared by controllers for interacting with tags."""

    def update(self, trans: ProvidesUserContext, payload: ItemTagsPayload) -> None:
        """Apply a new set of tags to an item; previous tags are deleted."""
        user = trans.user
        new_tags: Optional[str] = None
        if payload.item_tags and len(payload.item_tags.root) > 0:
            new_tags = ",".join(payload.item_tags.root)
        item = self._get_item(trans.tag_handler, payload)
        trans.tag_handler.delete_item_tags(user, item)
        trans.tag_handler.apply_item_tags(user, item, new_tags)
        trans.sa_session.commit()

    def _get_item(self, tag_handler: GalaxyTagHandlerSession, payload: ItemTagsPayload):
        """
        Get an item based on type and id.
        """
        item_class_name = str(payload.item_class)
        item_class = tag_handler.item_tag_assoc_info[item_class_name].item_class
        return tag_handler.sa_session.get(item_class, payload.item_id)

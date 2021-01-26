from typing import (
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.app import StructuredApp
from galaxy.managers.context import ProvidesUserContext


class ItemTagsPayload(BaseModel):
    item_id: str = Field(
        ...,  # This field is required
        title="Item ID",
        description="The `encoded identifier` of the item whose tags will be updated.",
    )
    item_class: str = Field(
        ...,  # This field is required
        title="Item class",
        description="The name of the class of the item.",
    )
    item_tags: Optional[List[str]] = Field(
        default=None,
        title="Item tags",
        description="The list of tags that will replace the current tags associated with the item.",
    )


class TagsManager:
    """Interface/service object shared by controllers for interacting with tags."""

    def __init__(self, app: StructuredApp):
        self._app = app

    def update(
            self,
            trans: ProvidesUserContext,
            payload: ItemTagsPayload,
    ) -> None:
        """Apply a new set of tags to an item; previous tags are deleted."""
        tag_handler = trans.app.tag_handler
        new_tags: Optional[str] = None
        if payload.item_tags and len(payload.item_tags) > 0:
            new_tags = ",".join(payload.item_tags)
        item = self._get_item(trans, payload)
        user = trans.user
        tag_handler.delete_item_tags(user, item)
        tag_handler.apply_item_tags(user, item, new_tags)
        trans.sa_session.flush()

    def _get_item(self, trans: ProvidesUserContext, payload: ItemTagsPayload):
        """
        Get an item based on type and id.
        """
        tag_handler = trans.app.tag_handler
        id = trans.security.decode_id(payload.item_id)
        item_class = tag_handler.item_tag_assoc_info[payload.item_class].item_class
        item = trans.sa_session.query(item_class).filter(item_class.id == id).first()
        return item

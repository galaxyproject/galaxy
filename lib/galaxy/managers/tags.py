from typing import List, Optional

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.app import StructuredApp
from galaxy.exceptions import MessageException
from galaxy.webapps.base.controller import UsesTagsMixin
from galaxy.webapps.base.webapp import GalaxyWebTransaction


class ItemTagsPayload(BaseModel):
    item_id: str = Field(
        ...,  # This field is required
        title="Item ID",
        description="The identifier of the item whose tags will be updated",
    )
    item_class: str = Field(
        ...,  # This field is required
        title="Item class",
        description="The name of the class of the item",
    )
    item_tags: Optional[List[str]] = Field(
        default=None,
        title="Item tags",
        description="The list of tags that will replace the current tags associated with the item",
    )


class TagsManager(UsesTagsMixin):
    """Interface/service object shared by controllers for interacting with tags."""

    def __init__(self, app: StructuredApp):
        self._app = app

    def update(
            self,
            trans: GalaxyWebTransaction,
            payload: ItemTagsPayload,
    ) -> None:
        """Apply a new set of tags to an item; previous tags are deleted."""
        if payload.item_id is None:
            raise MessageException("Please provide the item id (item_id).")
        if payload.item_class is None:
            raise MessageException("Please provide the item class (item_class).")

        new_tags: Optional[str] = None
        if payload.item_tags and len(payload.item_tags) > 0:
            new_tags = ",".join(payload.item_tags)
        item = self._get_item(trans, payload.item_class, trans.security.decode_id(payload.item_id))
        user = trans.user
        self.get_tag_handler(trans).delete_item_tags(user, item)
        self.get_tag_handler(trans).apply_item_tags(user, item, new_tags)
        trans.sa_session.flush()

    def _get_item(self, trans: GalaxyWebTransaction, item_class_name: str, id: int):
        """
        Get an item based on type and id.
        """
        item_class = self.get_tag_handler(trans).item_tag_assoc_info[item_class_name].item_class
        item = trans.sa_session.query(item_class).filter(item_class.id == id).first()
        return item

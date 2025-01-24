from galaxy.exceptions import (
    NoContentException,
    ObjectNotFound,
)
from galaxy.managers import base
from galaxy.managers.context import ProvidesAppContext
from galaxy.model.base import transaction
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.item_tags import ItemTagsCreatePayload
from galaxy.structured_app import MinimalManagerApp


class ItemTagsManager:
    """Interface/service object shared by controllers for interacting with item-tags."""

    def __init__(self, app: MinimalManagerApp) -> None:
        self._app = app
        self._tag_handler = app.tag_handler

    def index(self, trans: ProvidesAppContext, tagged_item_class: str, tagged_item_id: DecodedDatabaseIdField):
        """Displays a collection (list) of tags associated with an item."""
        tags = self._get_user_tags(trans, tagged_item_class, tagged_item_id)
        return [self._api_value(tag, trans, view="collection") for tag in tags]

    def show(
        self, trans: ProvidesAppContext, tagged_item_class: str, tagged_item_id: DecodedDatabaseIdField, tag_name: str
    ):
        """Displays information about a tag associated with an item."""
        tag = self._get_item_tag_assoc(trans, tagged_item_class, tagged_item_id, tag_name)
        if not tag:
            raise ObjectNotFound("Failed to retrieve specified tag.")
        return self._api_value(tag, trans)

    def create(
        self,
        trans: ProvidesAppContext,
        tagged_item_class: str,
        tagged_item_id: DecodedDatabaseIdField,
        tag_name: str,
        payload: ItemTagsCreatePayload,
    ):
        """Apply a new set of tags to an item."""
        value = payload.value
        tag = self._apply_item_tag(trans, tagged_item_class, tagged_item_id, tag_name, value)
        return self._api_value(tag, trans)

    def delete(
        self, trans: ProvidesAppContext, tagged_item_class: str, tagged_item_id: DecodedDatabaseIdField, tag_name: str
    ):
        """Remove a tag from an item."""
        deleted = self._remove_items_tag(trans, tagged_item_class, tagged_item_id, tag_name)
        if not deleted:
            raise NoContentException("Failed to delete specified tag.")
        return deleted

    def _get_tagged_item(self, trans, item_class_name, id, check_ownership=True):
        tagged_item = base.get_object(
            trans, id, item_class_name, check_ownership=check_ownership, check_accessible=True
        )
        return tagged_item

    def _get_user_tags(self, trans, item_class_name, id):
        user = trans.user
        tagged_item = self._get_tagged_item(trans, item_class_name, id)
        return [tag for tag in tagged_item.tags if tag.user == user]

    def _remove_items_tag(self, trans, item_class_name, id, tag_name):
        user = trans.user
        tagged_item = self._get_tagged_item(trans, item_class_name, id)
        deleted = tagged_item and self._tag_handler.remove_item_tag(user, tagged_item, tag_name)
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        return deleted

    def _apply_item_tag(self, trans, item_class_name, id, tag_name, tag_value=None):
        user = trans.user
        tagged_item = self._get_tagged_item(trans, item_class_name, id)
        tag_assoc = self._tag_handler.apply_item_tag(user, tagged_item, tag_name, tag_value)
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        return tag_assoc

    def _get_item_tag_assoc(self, trans, item_class_name, id, tag_name):
        user = trans.user
        tagged_item = self._get_tagged_item(trans, item_class_name, id)
        return self._tag_handler._get_item_tag_assoc(user, tagged_item, tag_name)

    def _api_value(self, tag, trans, view="element"):
        return tag.to_dict(view=view, value_mapper={"id": trans.security.encode_id})

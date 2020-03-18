"""
API Controller providing Galaxy Tags
"""
import logging

from galaxy.exceptions import MessageException
from galaxy.web import expose_api
from galaxy.webapps.base.controller import BaseAPIController, UsesTagsMixin

log = logging.getLogger(__name__)


class TagsController(BaseAPIController, UsesTagsMixin):

    # Retag an item. All previous tags are deleted and new tags are applied.
    @expose_api
    def update(self, trans, payload, **kwd):
        """
        *PUT /api/tags/
        Apply a new set of tags to an item; previous tags are deleted.
        """
        item_id = payload.get("item_id")
        item_class = payload.get("item_class")
        item_tags = payload.get("item_tags")
        if item_id is None:
            raise MessageException("Please provide the item id (item_id).")
        if item_class is None:
            raise MessageException("Please provide the item class (item_class).")
        if item_tags and len(item_tags) > 0:
            item_tags = ",".join(item_tags)
        item = self._get_item(trans, item_class, trans.security.decode_id(item_id))
        user = trans.user
        self.get_tag_handler(trans).delete_item_tags(user, item)
        self.get_tag_handler(trans).apply_item_tags(user, item, item_tags)
        trans.sa_session.flush()

    def _get_item(self, trans, item_class_name, id):
        """
        Get an item based on type and id.
        """
        item_class = self.get_tag_handler(trans).item_tag_assoc_info[item_class_name].item_class
        item = trans.sa_session.query(item_class).filter(item_class.id == id).first()
        return item

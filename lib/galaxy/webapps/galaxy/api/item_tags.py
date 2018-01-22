"""
API operations related to tagging items.
"""
import logging

from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import (
    BaseAPIController,
    UsesTagsMixin
)

log = logging.getLogger(__name__)


class BaseItemTagsController(BaseAPIController, UsesTagsMixin):
    """
    """
    @expose_api
    def index(self, trans, **kwd):
        """
        """
        tags = self._get_user_tags(trans, self.tagged_item_class, kwd[self.tagged_item_id])
        return [self._api_value(tag, trans, view='collection') for tag in tags]

    @expose_api
    def show(self, trans, tag_name, **kwd):
        """
        """
        tag = self._get_item_tag_assoc(trans, self.tagged_item_class, kwd[self.tagged_item_id], tag_name)
        if not tag:
            raise exceptions.ObjectNotFound("Failed to retrieve specified tag.")
        return self._api_value(tag, trans)

    @expose_api
    def create(self, trans, tag_name, payload=None, **kwd):
        """
        """
        payload = payload or {}
        value = payload.get("value", None)
        tag = self._apply_item_tag(trans, self.tagged_item_class, kwd[self.tagged_item_id], tag_name, value)
        return self._api_value(tag, trans)

    # Not handling these differently at this time
    update = create

    @expose_api
    def delete(self, trans, tag_name, **kwd):
        """
        """
        deleted = self._remove_items_tag(trans, self.tagged_item_class, kwd[self.tagged_item_id], tag_name)
        if not deleted:
            raise exceptions.RequestParameterInvalidException("Failed to delete specified tag.")
        # TODO: ugh - 204 would be better
        return 'OK'

    def _api_value(self, tag, trans, view='element'):
        return tag.to_dict(view=view, value_mapper={'id': trans.security.encode_id})


class HistoryContentTagsController(BaseItemTagsController):
    controller_name = "history_content_tags"
    tagged_item_class = "HistoryDatasetAssociation"
    tagged_item_id = "history_content_id"


class HistoryTagsController(BaseItemTagsController):
    controller_name = "history_tags"
    tagged_item_class = "History"
    tagged_item_id = "history_id"


class WorkflowTagsController(BaseItemTagsController):
    controller_name = "workflow_tags"
    tagged_item_class = "StoredWorkflow"
    tagged_item_id = "workflow_id"

# TODO: Visualization and Pages once APIs for those are available

"""
API operations related to tagging items.
"""
import logging
from galaxy import web
from galaxy.web.base.controller import BaseAPIController, UsesTagsMixin
from paste.httpexceptions import HTTPBadRequest

log = logging.getLogger( __name__ )


class BaseItemTagsController( BaseAPIController, UsesTagsMixin ):
    """
    """
    @web.expose_api
    def index( self, trans, **kwd ):
        """
        """
        tags = self._get_user_tags(trans, self.tagged_item_class, kwd[self.tagged_item_id])
        return [ self._api_value( tag, trans, view='collection' ) for tag in tags ]

    @web.expose_api
    def show( self, trans, tag_name, **kwd ):
        """
        """
        tag = self._get_item_tag_assoc( trans, self.tagged_item_class, kwd[self.tagged_item_id], tag_name )
        if not tag:
            raise HTTPBadRequest("Failed to retrieve specified tag.")
        return self._api_value( tag, trans )

    @web.expose_api
    def create( self, trans, tag_name, payload=None, **kwd ):
        """
        """
        payload = payload or {}
        value = payload.get("value", None)
        tag = self._apply_item_tag( trans, self.tagged_item_class, kwd[self.tagged_item_id], tag_name, value )
        return self._api_value( tag, trans )

    # Not handling these differently at this time
    update = create

    @web.expose_api
    def delete( self, trans, tag_name, **kwd ):
        """
        """
        deleted = self._remove_items_tag( trans, self.tagged_item_class, kwd[self.tagged_item_id], tag_name )
        if not deleted:
            raise HTTPBadRequest("Failed to delete specified tag.")
        return 'OK'

    def _api_value( self, tag, trans, view='element' ):
        return tag.to_dict( view=view, value_mapper={ 'id': trans.security.encode_id } )


class HistoryContentTagsController( BaseItemTagsController ):
    controller_name = "history_content_tags"
    tagged_item_class = "HistoryDatasetAssociation"
    tagged_item_id = "history_content_id"


class HistoryTagsController( BaseItemTagsController ):
    controller_name = "history_tags"
    tagged_item_class = "History"
    tagged_item_id = "history_id"


class WorkflowTagsController( BaseItemTagsController ):
    controller_name = "workflow_tags"
    tagged_item_class = "StoredWorkflow"
    tagged_item_id = "workflow_id"

# TODO: Visualization and Pages once APIs for those are available

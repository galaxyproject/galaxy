"""
API operations on annotations.
"""
import logging
from galaxy import web
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web.base.controller import BaseAPIController, HTTPNotImplemented, UsesHistoryDatasetAssociationMixin, UsesHistoryMixin, UsesStoredWorkflowMixin

log = logging.getLogger( __name__ )


class BaseAnnotationsController( BaseAPIController, UsesHistoryMixin, UsesHistoryDatasetAssociationMixin, UsesStoredWorkflowMixin, UsesAnnotations ):

    @web.expose_api
    def index( self, trans, **kwd ):
        idnum = kwd[self.tagged_item_id]
        item = self._get_item_from_id(trans, idnum)
        if item is not None:
            return self.get_item_annotation_str( trans.sa_session, trans.get_user(), item )

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        if "text" not in payload:
            return ""
        idnum = kwd[self.tagged_item_id]
        item = self._get_item_from_id(trans, idnum)
        if item is not None:
            new_annotation = payload.get("text")
            # Sanitize annotation before adding it.
            new_annotation = sanitize_html( new_annotation, 'utf-8', 'text/html' )

            self.add_item_annotation( trans.sa_session, trans.get_user(), item, new_annotation )
            trans.sa_session.flush()
            return new_annotation
        return ""

    @web.expose_api
    def delete( self, trans, **kwd ):
        idnum = kwd[self.tagged_item_id]
        item = self._get_item_from_id(trans, idnum)
        if item is not None:
            return self.delete_item_annotation( trans.sa_session, trans.get_user(), item )

    @web.expose_api
    def undelete( self, trans, **kwd ):
        raise HTTPNotImplemented()


class HistoryAnnotationsController(BaseAnnotationsController):
    controller_name = "history_annotations"
    tagged_item_id = "history_id"

    def _get_item_from_id(self, trans, idstr):
        hist = self.get_history( trans, idstr )
        return hist


class HistoryContentAnnotationsController(BaseAnnotationsController):
    controller_name = "history_content_annotations"
    tagged_item_id = "history_content_id"

    def _get_item_from_id(self, trans, idstr):
        hda = self.get_dataset(trans, idstr)
        return hda


class WorkflowAnnotationsController(BaseAnnotationsController):
    controller_name = "workflow_annotations"
    tagged_item_id = "workflow_id"

    def _get_item_from_id(self, trans, idstr):
        hda = self.get_stored_workflow(trans, idstr)
        return hda

"""
API operations on annotations.
"""
import logging

from galaxy import (
    exceptions,
    managers
)
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import (
    BaseAPIController,
    UsesStoredWorkflowMixin
)

log = logging.getLogger(__name__)


class BaseAnnotationsController(BaseAPIController, UsesStoredWorkflowMixin, UsesAnnotations):

    @expose_api
    def index(self, trans, **kwd):
        idnum = kwd[self.tagged_item_id]
        item = self._get_item_from_id(trans, idnum)
        if item is not None:
            return self.get_item_annotation_str(trans.sa_session, trans.get_user(), item)

    @expose_api
    def create(self, trans, payload, **kwd):
        if "text" not in payload:
            return ""
        idnum = kwd[self.tagged_item_id]
        item = self._get_item_from_id(trans, idnum)
        if item is not None:
            new_annotation = payload.get("text")
            # TODO: sanitize on display not entry
            new_annotation = sanitize_html(new_annotation)

            self.add_item_annotation(trans.sa_session, trans.get_user(), item, new_annotation)
            trans.sa_session.flush()
            return new_annotation
        return ""

    @expose_api
    def delete(self, trans, **kwd):
        idnum = kwd[self.tagged_item_id]
        item = self._get_item_from_id(trans, idnum)
        if item is not None:
            return self.delete_item_annotation(trans.sa_session, trans.get_user(), item)

    @expose_api
    def undelete(self, trans, **kwd):
        raise exceptions.NotImplemented()


class HistoryAnnotationsController(BaseAnnotationsController):
    controller_name = "history_annotations"
    tagged_item_id = "history_id"

    def __init__(self, app):
        super(HistoryAnnotationsController, self).__init__(app)
        self.history_manager = managers.histories.HistoryManager(app)

    def _get_item_from_id(self, trans, idstr):
        decoded_idstr = self.decode_id(idstr)
        history = self.history_manager.get_accessible(decoded_idstr, trans.user, current_history=trans.history)
        return history


class HistoryContentAnnotationsController(BaseAnnotationsController):
    controller_name = "history_content_annotations"
    tagged_item_id = "history_content_id"

    def __init__(self, app):
        super(HistoryContentAnnotationsController, self).__init__(app)
        self.hda_manager = managers.hdas.HDAManager(app)

    def _get_item_from_id(self, trans, idstr):
        decoded_idstr = self.decode_id(idstr)
        hda = self.hda_manager.get_accessible(decoded_idstr, trans.user)
        hda = self.hda_manager.error_if_uploading(hda)
        return hda


class WorkflowAnnotationsController(BaseAnnotationsController):
    controller_name = "workflow_annotations"
    tagged_item_id = "workflow_id"

    def _get_item_from_id(self, trans, idstr):
        hda = self.get_stored_workflow(trans, idstr)
        return hda

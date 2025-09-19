"""
API operations on annotations.
"""

import logging
from abc import abstractmethod

from galaxy import (
    exceptions,
    managers,
)
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import expose_api
from galaxy.webapps.base.controller import UsesStoredWorkflowMixin
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class BaseAnnotationsController(BaseGalaxyAPIController, UsesStoredWorkflowMixin, UsesAnnotations):
    tagged_item_id: str

    @expose_api
    def index(self, trans: ProvidesHistoryContext, **kwd):
        idnum = kwd[self.tagged_item_id]
        if (item := self._get_item_from_id(trans, idnum)) is not None:
            return self.get_item_annotation_str(trans.sa_session, trans.user, item)

    @expose_api
    def create(self, trans: ProvidesHistoryContext, payload: dict, **kwd):
        if "text" not in payload:
            return ""
        idnum = kwd[self.tagged_item_id]
        if (item := self._get_item_from_id(trans, idnum)) is not None:
            new_annotation = payload.get("text")
            # TODO: sanitize on display not entry
            new_annotation = sanitize_html(new_annotation)

            self.add_item_annotation(trans.sa_session, trans.user, item, new_annotation)
            trans.sa_session.commit()
            return new_annotation
        return ""

    @expose_api
    def delete(self, trans: ProvidesHistoryContext, **kwd):
        idnum = kwd[self.tagged_item_id]
        if (item := self._get_item_from_id(trans, idnum)) is not None:
            return self.delete_item_annotation(trans.sa_session, trans.user, item)

    @expose_api
    def undelete(self, trans: ProvidesHistoryContext, **kwd):
        raise exceptions.NotImplemented()

    @abstractmethod
    def _get_item_from_id(self, trans: ProvidesHistoryContext, idstr):
        """Return item with annotation association."""


class HistoryAnnotationsController(BaseAnnotationsController):
    controller_name = "history_annotations"
    tagged_item_id = "history_id"
    history_manager: managers.histories.HistoryManager = depends(managers.histories.HistoryManager)

    def _get_item_from_id(self, trans: ProvidesHistoryContext, idstr):
        decoded_idstr = self.decode_id(idstr)
        history = self.history_manager.get_accessible(decoded_idstr, trans.user, current_history=trans.history)
        return history


class HistoryContentAnnotationsController(BaseAnnotationsController):
    controller_name = "history_content_annotations"
    tagged_item_id = "history_content_id"
    hda_manager: managers.hdas.HDAManager = depends(managers.hdas.HDAManager)

    def _get_item_from_id(self, trans: ProvidesHistoryContext, idstr):
        decoded_idstr = self.decode_id(idstr)
        hda = self.hda_manager.get_accessible(decoded_idstr, trans.user)
        hda = self.hda_manager.error_if_uploading(hda)
        return hda


class WorkflowAnnotationsController(BaseAnnotationsController):
    controller_name = "workflow_annotations"
    tagged_item_id = "workflow_id"

    def _get_item_from_id(self, trans: ProvidesHistoryContext, idstr):
        hda = self.get_stored_workflow(trans, idstr)
        return hda

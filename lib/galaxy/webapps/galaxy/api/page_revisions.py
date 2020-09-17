"""
API for updating Galaxy Pages
"""
import logging

from galaxy.managers.base import get_object
from galaxy.managers.pages import PageManager
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.web import expose_api
from galaxy.webapps.base.controller import (
    BaseAPIController,
    SharableItemSecurityMixin,
    SharableMixin
)

log = logging.getLogger(__name__)


class PageRevisionsController(BaseAPIController, SharableItemSecurityMixin, UsesAnnotations, SharableMixin):

    def __init__(self, app):
        super().__init__(app)
        self.manager = PageManager(app)

    @expose_api
    def index(self, trans, page_id, **kwd):
        """
        index( self, trans, page_id, **kwd )
        * GET /api/pages/{page_id}/revisions
            return a list of Page revisions

        :param page_id: Display the revisions of Page with ID=page_id

        :rtype:     list
        :returns:   dictionaries containing different revisions of the page
        """
        page = get_object(trans, page_id, 'Page', check_ownership=False, check_accessible=True)
        r = trans.sa_session.query(trans.app.model.PageRevision).filter_by(page_id=page.id)
        out = []
        for page in r:
            as_dict = self.encode_all_ids(trans, page.to_dict(), True)
            self.manager.rewrite_content_for_export(trans, as_dict)
            out.append(as_dict)
        return out

    @expose_api
    def create(self, trans, page_id, payload, **kwd):
        """
        create( self, trans, page_id, payload **kwd )
        * POST /api/pages/{page_id}/revisions
            Create a new revision for a page

        :param page_id: Add revision to Page with ID=page_id
        :param payload: A dictionary containing::
            'content'   = New content of new page revision

        :rtype:     dictionary
        :returns:   Dictionary with 'success' or 'error' element to indicate the result of the request
        """
        page = get_object(trans, page_id, 'Page', check_ownership=True)
        page_revision = self.manager.save_new_revision(trans, page, payload)
        rval = self.encode_all_ids(trans, page_revision.to_dict(view="element"), True)
        self.manager.rewrite_content_for_export(trans, rval)
        return rval

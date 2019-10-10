"""
API for updating Galaxy Pages
"""
import logging

from galaxy import exceptions
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import (
    BaseAPIController,
    SharableItemSecurityMixin,
    SharableMixin
)

log = logging.getLogger(__name__)


class PageRevisionsController(BaseAPIController, SharableItemSecurityMixin, UsesAnnotations, SharableMixin):

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
        page = self._get_page(trans, page_id)
        self._verify_page_ownership(trans, page)

        r = trans.sa_session.query(trans.app.model.PageRevision).filter_by(page_id=trans.security.decode_id(page_id))
        out = []
        for page in r:
            out.append(self.encode_all_ids(trans, page.to_dict(), True))
        return out

    @expose_api
    def create(self, trans, page_id, payload, **kwd):
        """
        create( self, trans, page_id, payload **kwd )
        * POST /api/pages/{page_id}/revisions
            Create a new revision for a page

        :param page_id: Add revision to Page with ID=page_id
        :param payload: A dictionary containing::
            'title'     = New title of the page
            'content'   = New content of the page

        :rtype:     dictionary
        :returns:   Dictionary with 'success' or 'error' element to indicate the result of the request
        """
        content = payload.get("content", None)
        if not content:
            raise exceptions.ObjectAttributeMissingException("content undefined or empty")

        page = self._get_page(trans, page_id)
        self._verify_page_ownership(trans, page)

        if 'title' in payload:
            title = payload['title']
        else:
            title = page.title

        content = sanitize_html(content)

        page_revision = trans.app.model.PageRevision()
        page_revision.title = title
        page_revision.page = page
        page.latest_revision = page_revision
        page_revision.content = content

        # Persist
        session = trans.sa_session
        session.flush()

        return page_revision.to_dict(view="element")

    def _get_page(self, trans, page_id):
        page = None
        try:
            page = trans.sa_session.query(trans.app.model.Page).get(trans.security.decode_id(page_id))
        except Exception:
            pass
        if not page:
            raise exceptions.ObjectNotFound()
        return page

    def _verify_page_ownership(self, trans, page):
        if not self.security_check(trans, page, True, True):
            raise exceptions.ItemOwnershipException()

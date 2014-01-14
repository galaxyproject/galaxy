"""
API for updating Galaxy Pages
"""
import logging
from galaxy import web
from galaxy.web.base.controller import SharableItemSecurityMixin, BaseAPIController, SharableMixin
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.util.sanitize_html import sanitize_html

log = logging.getLogger( __name__ )


class PageRevisionsController( BaseAPIController, SharableItemSecurityMixin, UsesAnnotations, SharableMixin ):

    @web.expose_api
    def index( self, trans, page_id, **kwd ):
        """
        index( self, trans, page_id, **kwd )
        * GET /api/pages/{page_id}/revisions
            return a list of Page revisions

        :param page_id: Display the revisions of Page with ID=page_id

        :rtype:     list
        :returns:   dictionaries containing different revisions of the page
        """
        r = trans.sa_session.query( trans.app.model.PageRevision ).filter_by( page_id=trans.security.decode_id(page_id) )
        out = []
        for page in r:
            if self.security_check( trans, page, True, True ):
                out.append( self.encode_all_ids( trans, page.to_dict(), True) )
        return out

    @web.expose_api
    def create( self, trans, page_id, payload, **kwd ):
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
        error_str = ""

        if not page_id:
            error_str = "page_id is required"
        elif not payload.get("content", None):
            error_str = "content is required"
        else:

            # Create the new stored page
            page = trans.sa_session.query( trans.app.model.Page ).get( trans.security.decode_id(page_id) )
            if page is None:
                return { "error" : "page not found"}

            if not self.security_check( trans, page, True, True ):
                return { "error" : "page not found"}

            if 'title' in payload:
                title = payload['title']
            else:
                title = page.title

            content = payload.get("content", "")
            content = sanitize_html( content, 'utf-8', 'text/html' )

            page_revision = trans.app.model.PageRevision()
            page_revision.title = title
            page_revision.page = page
            page.latest_revision = page_revision
            page_revision.content = content
            # Persist
            session = trans.sa_session
            session.flush()

            return { "success" : "revision posted" }

        return { "error" : error_str }

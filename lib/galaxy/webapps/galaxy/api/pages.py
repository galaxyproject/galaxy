"""
API for updating Galaxy Pages
"""
import logging

from galaxy.managers.pages import (
    PagesManager,
)
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    expose_api_raw_anonymous_and_sessionless
)
from galaxy.webapps.base.controller import (
    BaseAPIController,
)

log = logging.getLogger(__name__)


class PagesController(BaseAPIController):
    """
    RESTful controller for interactions with pages.
    """

    def __init__(self, app):
        super().__init__(app)
        self.manager = PagesManager(app)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, deleted=False, **kwd):
        """
        index( self, trans, deleted=False, **kwd )
        * GET /api/pages
            return a list of Pages viewable by the user

        :param deleted: Display deleted pages

        :rtype:     list
        :returns:   dictionaries containing summary or detailed Page information
        """
        return self.manager.index(trans, deleted)

    @expose_api
    def create(self, trans, payload, **kwd):
        """
        create( self, trans, payload, **kwd )
        * POST /api/pages
            Create a page and return dictionary containing Page summary

        :param  payload:    dictionary structure containing::
            'slug'           = The title slug for the page URL, must be unique
            'title'          = Title of the page
            'content'        = contents of the first page revision (type dependent on content_format)
            'content_format' = 'html' or 'markdown'
            'annotation'     = Annotation that will be attached to the page

        :rtype:     dict
        :returns:   Dictionary return of the Page.to_dict call
        """
        return self.manager.create(trans, payload)

    @expose_api
    def delete(self, trans, id, **kwd):
        """
        delete( self, trans, id, **kwd )
        * DELETE /api/pages/{id}
            Create a page and return dictionary containing Page summary

        :param  id:    ID of page to be deleted

        :rtype:     dict
        :returns:   Dictionary with 'success' or 'error' element to indicate the result of the request
        """
        self.manager.delete(trans, id)

    @expose_api_anonymous_and_sessionless
    def show(self, trans, id, **kwd):
        """
        show( self, trans, id, **kwd )
        * GET /api/pages/{id}
            View a page summary and the content of the latest revision

        :param  id:    ID of page to be displayed

        :rtype:     dict
        :returns:   Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        return self.manager.show(trans, id)

    @expose_api_raw_anonymous_and_sessionless
    def show_pdf(self, trans, id, **kwd):
        """
        GET /api/pages/{id}.pdf

        View a page summary and the content of the latest revision as PDF.

        :param  id: ID of page to be displayed

        :rtype: dict
        :returns: Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        return self.manager.show_pdf(trans, id)

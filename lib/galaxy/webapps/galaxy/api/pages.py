"""
API for updating Galaxy Pages
"""
import logging
from galaxy import web
from galaxy.web.base.controller import SharableItemSecurityMixin, BaseAPIController, SharableMixin
from galaxy.model.search import GalaxySearchEngine
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.exceptions import ItemAccessibilityException
from galaxy.util.sanitize_html import sanitize_html

log = logging.getLogger( __name__ )

class PagesController( BaseAPIController, SharableItemSecurityMixin, UsesAnnotations, SharableMixin ):

    @web.expose_api
    def index( self, trans, deleted='False', **kwd ):
        """
        index( self, trans, deleted='False', **kwd )
        * GET /api/pages
            return a list of Pages viewable by the user

        :param deleted: Display deleted pages

        :rtype:     list
        :returns:   dictionaries containing summary or detailed Page information
        """
        r = trans.sa_session.query( trans.app.model.Page )
        if not deleted:
            r = r.filter_by(deleted=False)
        out = []
        for row in r:
            out.append( self.encode_all_ids( trans, row.to_dict(), True) )
        return out


    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        create( self, trans, payload, **kwd )
        * POST /api/pages
            Create a page and return dictionary containing Page summary

        :param  payload:    dictionary structure containing::
            'slug'       = The title slug for the page URL, must be unique
            'title'      = Title of the page
            'content'    = HTML contents of the page
            'annotation' = Annotation that will be attached to the page

        :rtype:     dict
        :returns:   Dictionary return of the Page.to_dict call
        """
        user = trans.get_user()
        error_str = ""
        
        if not payload.get("title", None):
            error_str = "Page name is required"
        elif not payload.get("slug", None):
            error_str = "Page id is required"
        elif not self._is_valid_slug( payload["slug"] ):
            error_str = "Page identifier must consist of only lowercase letters, numbers, and the '-' character"
        elif trans.sa_session.query( trans.app.model.Page ).filter_by( user=user, slug=payload["slug"], deleted=False ).first():
            error_str = "Page id must be unique"
        else:
            # Create the new stored page
            page = trans.app.model.Page()
            page.title = payload['title']
            page.slug = payload['slug']
            page_annotation = sanitize_html( payload.get("annotation",""), 'utf-8', 'text/html' )
            self.add_item_annotation( trans.sa_session, trans.get_user(), page, page_annotation )
            page.user = user
            # And the first (empty) page revision
            page_revision = trans.app.model.PageRevision()
            page_revision.title = payload['title']
            page_revision.page = page
            page.latest_revision = page_revision
            page_revision.content = payload.get("content", "")
            # Persist
            session = trans.sa_session
            session.add( page )
            session.flush()

            rval = self.encode_all_ids( trans, page.to_dict(), True) 
            return rval
        
        return { "error" : error_str }    


    @web.expose_api
    def delete( self, trans, id, **kwd ):
        """
        delete( self, trans, id, **kwd )
        * DELETE /api/pages/{id}
            Create a page and return dictionary containing Page summary

        :param  id:    ID of page to be deleted

        :rtype:     dict
        :returns:   Dictionary with 'success' or 'error' element to indicate the result of the request 
        """
        page_id = id;
        try:
            page = trans.sa_session.query(self.app.model.Page).get(trans.security.decode_id(page_id))
        except Exception, e:
            return { "error" : "Page with ID='%s' can not be found\n Exception: %s" % (page_id, str( e )) }

        # check to see if user has permissions to selected workflow
        if page.user != trans.user and not trans.user_is_admin():
            return { "error" : "Workflow is not owned by or shared with current user" }

        #Mark a workflow as deleted
        page.deleted = True
        trans.sa_session.flush()
        return {"success" : "Deleted", "id" : page_id}

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        show( self, trans, id, **kwd )
        * GET /api/pages/{id}
            View a page summary and the content of the latest revision

        :param  id:    ID of page to be displayed

        :rtype:     dict
        :returns:   Dictionary return of the Page.to_dict call with the 'content' field populated by the most recent revision
        """
        page = trans.sa_session.query( trans.app.model.Page ).get( trans.security.decode_id( id ) )
        rval = self.encode_all_ids( trans, page.to_dict(), True) 
        rval['content'] = page.latest_revision.content
        return rval
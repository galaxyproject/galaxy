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
        r = trans.sa_session.query( trans.app.model.Page )
        out = []
        for row in r:
            out.append( self.encode_all_ids( trans, row.to_dict(), True) )
        return out


    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        payload keys:
            slug
            title
            content
            annotation
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
    def show( self, trans, id, deleted='False', **kwd ):
        page = trans.sa_session.query( trans.app.model.Page ).get( trans.security.decode_id( id ) )
        rval = self.encode_all_ids( trans, page.to_dict(), True) 
        rval['content'] = page.latest_revision.content
        return rval
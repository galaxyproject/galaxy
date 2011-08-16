"""
API operations on a history.
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

class HistoriesController( BaseController ):

    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/histories
        Displays a collection (list) of histories.
        """
        try:
            query = trans.sa_session.query( trans.app.model.History ).filter( trans.app.model.History.table.c.deleted == False )
            current_user_role_ids = [ role.id for role in trans.get_current_user_roles() ]
            user = trans.get_user()
            query = query.filter_by( user=user, deleted=False )
        except Exception, e:
            log.debug("Error in history API: %s" % str(e))
        rval = []
        try:
            for history in query:
                item = history.get_api_value()
                item['url'] = url_for( 'history', id=trans.security.encode_id( history.id ) )
                item['id'] = trans.security.encode_id( item['id'] )
                rval.append( item )
        except Exception, e:
            log.debug("Error in history API at constructing return list: %s" % str(e))
        return rval

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/histories/{encoded_library_id}
        Displays information about a history.
        """
        history_id = id
        params = util.Params( kwd )
        try:
            decoded_history_id = trans.security.decode_id( history_id )
        except TypeError:
            trans.response.status = 400
            return "Malformed history id ( %s ) specified, unable to decode." % str( library_id )
        try:
            history = trans.sa_session.query( trans.app.model.History ).get( decoded_history_id )
        except:
            history = None
        try:
            if not history or not ( trans.user_is_admin() or trans.app.security_agent.can_access_history( trans.get_current_user_roles(), history ) ):
                trans.response.status = 400
                return "Invalid history id ( %s ) specified." % str( history_id )
            item = history.get_api_value( view='element' )
            item['contents_url'] = url_for( 'history_contents', history_id=history_id )
        except Exception, e:
            log.debug("Error in history API at showing history detail: %s" % str(e))
        return item

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/histories
        Creates a new history.
        """
        trans.response.status = 403
        return "Not implemented."

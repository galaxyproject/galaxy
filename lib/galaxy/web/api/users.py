"""
API operations on User objects.
"""
import logging
from galaxy.web.base.controller import BaseController, url_for
from galaxy import web
from elementtree.ElementTree import XML

log = logging.getLogger( __name__ )

class UserAPIController( BaseController ):
    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/users
        Displays a collection (list) of users.
        """
        if not trans.user_is_admin():
            trans.response.status = 403
            return "You are not authorized to view the list of users."
        rval = []
        for user in trans.sa_session.query( trans.app.model.User ).filter( trans.app.model.User.table.c.deleted == False ):
            item = user.get_api_value( value_mapper={ 'id': trans.security.encode_id } )
            encoded_id = trans.security.encode_id( user.id )
            item['url'] = url_for( 'user', id=encoded_id )
            rval.append( item )
        return rval

    @web.expose_api
    def show( self, trans, id, **kwd ):
        """
        GET /api/users/{encoded_user_id}
        Displays information about a user.
        """
        if not trans.user_is_admin():
            trans.response.status = 403
            return "You are not authorized to view user info."
        user_id = id
        try:
            decoded_user_id = trans.security.decode_id( user_id )
        except TypeError:
            trans.response.status = 400
            return "Malformed user id ( %s ) specified, unable to decode." % str( user_id )
        try:
            user = trans.sa_session.query( trans.app.model.User ).get( decoded_user_id )
        except:
            trans.response.status = 400
            return "That user does not exist."
        item = user.get_api_value( view='element', value_mapper={ 'id': trans.security.encode_id } )    
        item['url'] = url_for( 'user', id=user_id )
        return item
    
    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/users
        Creates a new user.
        """
        trans.response.status = 403
        return "Not implemented."

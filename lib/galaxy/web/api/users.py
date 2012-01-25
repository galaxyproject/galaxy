"""
API operations on User objects.
"""
import logging
from galaxy.web.base.controller import BaseAPIController, url_for
from galaxy import web, util
from elementtree.ElementTree import XML
from paste.httpexceptions import *

log = logging.getLogger( __name__ )

class UserAPIController( BaseAPIController ):
    @web.expose_api
    def index( self, trans, deleted='False', **kwd ):
        """
        GET /api/users
        GET /api/users/deleted
        Displays a collection (list) of users.
        """
        rval = []
        query = trans.sa_session.query( trans.app.model.User )
        deleted = util.string_as_bool( deleted )
        if deleted:
            route = 'deleted_user'
            query = query.filter( trans.app.model.User.table.c.deleted == True )
            # only admins can see deleted users
            if not trans.user_is_admin():
                return []
        else:
            route = 'user'
            query = query.filter( trans.app.model.User.table.c.deleted == False )
            # special case: user can see only their own user
            if not trans.user_is_admin():
                item = trans.user.get_api_value( value_mapper={ 'id': trans.security.encode_id } )
                item['url'] = url_for( route, id=item['id'] )
                return item
        for user in query:
            item = user.get_api_value( value_mapper={ 'id': trans.security.encode_id } )
            item['url'] = url_for( route, id=item['id'] )
            rval.append( item )
        return rval

    @web.expose_api
    def show( self, trans, id, deleted='False', **kwd ):
        """
        GET /api/users/{encoded_user_id}
        GET /api/users/deleted/{encoded_user_id}
        Displays information about a user.
        """
        deleted = util.string_as_bool( deleted )
        try:
            user = self.get_user( trans, id, deleted=deleted )
            if not trans.user_is_admin():
                assert trans.user == user
                assert not user.deleted
        except:
            if trans.user_is_admin():
                raise
            else:
                raise HTTPBadRequest( detail='Invalid user id ( %s ) specified' % id )
        item = user.get_api_value( view='element', value_mapper={ 'id': trans.security.encode_id,
                                                                  'total_disk_usage': float } )    
        return item
    
    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        /api/users
        Creates a new Galaxy user.
        """
        if not trans.app.config.allow_user_creation:
            raise HTTPNotImplemented( detail='User creation is not allowed in this Galaxy instance' )
        if trans.app.config.use_remote_user and trans.user_is_admin():
            user = trans.get_or_create_remote_user(remote_user_email=payload['remote_user_email'])
            item = user.get_api_value( view='element', value_mapper={ 'id': trans.security.encode_id,
                                                                      'total_disk_usage': float } )    
        else:
            raise HTTPNotImplemented()
        return item

    @web.expose_api
    def update( self, trans, **kwd ):
        raise HTTPNotImplemented()

    @web.expose_api
    def delete( self, trans, **kwd ):
        raise HTTPNotImplemented()

    @web.expose_api
    def undelete( self, trans, **kwd ):
        raise HTTPNotImplemented()

"""
API operations on User objects.
"""
import logging
from paste.httpexceptions import HTTPBadRequest, HTTPNotImplemented
from galaxy import util, web
from galaxy.web.base.controller import BaseAPIController, url_for

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
                item['quota_percent'] = trans.app.quota_agent.get_percent( trans=trans )
                return [item]

        for user in query:
            item = user.get_api_value( value_mapper={ 'id': trans.security.encode_id } )
            #TODO: move into api_values
            item['quota_percent'] = trans.app.quota_agent.get_percent( trans=trans )
            item['url'] = url_for( route, id=item['id'] )
            rval.append( item )
        return rval

    @web.expose_api
    def show( self, trans, id, deleted='False', **kwd ):
        """
        GET /api/users/{encoded_user_id}
        GET /api/users/deleted/{encoded_user_id}
        GET /api/users/current
        Displays information about a user.
        """
        deleted = util.string_as_bool( deleted )
        try:
            # user is requesting data about themselves
            if id == "current":
                # ...and is anonymous - return usage and quota (if any)
                if not trans.user:
                    item = self.anon_user_api_value( trans )
                    return item

                # ...and is logged in - return full
                else:
                    user = trans.user
            else:
                user = self.get_user( trans, id, deleted=deleted )

            # check that the user is requesting themselves (and they aren't del'd) unless admin
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
        #TODO: move into api_values (needs trans, tho - can we do that with api_keys/@property??)
        #TODO: works with other users (from admin)??
        item['quota_percent'] = trans.app.quota_agent.get_percent( trans=trans )

        return item
    
    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/users
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

    #TODO: move to more basal, common resource than this
    def anon_user_api_value( self, trans ):
        """
        Returns data for an anonymous user, truncated to only usage and quota_percent
        """
        usage = trans.app.quota_agent.get_usage( trans )
        percent = trans.app.quota_agent.get_percent( trans=trans, usage=usage )
        return {
            'total_disk_usage'      : int( usage ),
            'nice_total_disk_usage' : util.nice_size( usage ),
            'quota_percent'         : percent
        }

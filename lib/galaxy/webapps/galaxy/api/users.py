"""
API operations on User objects.
"""
import logging
from paste.httpexceptions import HTTPBadRequest, HTTPNotImplemented

from galaxy import util, web, exceptions
from galaxy.security.validate_user_input import validate_email
from galaxy.security.validate_user_input import validate_password
from galaxy.security.validate_user_input import validate_publicname
from galaxy.web.base.controller import BaseAPIController, UsesTagsMixin
from galaxy.web.base.controller import CreatesApiKeysMixin
from galaxy.web.base.controller import CreatesUsersMixin

log = logging.getLogger( __name__ )


class UserAPIController( BaseAPIController, UsesTagsMixin, CreatesUsersMixin, CreatesApiKeysMixin ):

    @web.expose_api
    def index( self, trans, deleted='False', f_email=None, **kwd ):
        """
        GET /api/users
        GET /api/users/deleted
        Displays a collection (list) of users.
        """
        rval = []
        query = trans.sa_session.query( trans.app.model.User )
        deleted = util.string_as_bool( deleted )
        if f_email:
            query = query.filter(trans.app.model.User.email.like("%%%s%%" % f_email))
        if deleted:
            query = query.filter( trans.app.model.User.table.c.deleted == True )  # noqa
            # only admins can see deleted users
            if not trans.user_is_admin():
                return []
        else:
            query = query.filter( trans.app.model.User.table.c.deleted == False )  # noqa
            # special case: user can see only their own user
            if not trans.user_is_admin():
                item = trans.user.to_dict( value_mapper={ 'id': trans.security.encode_id } )
                return [item]
        for user in query:
            item = user.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            # TODO: move into api_values
            rval.append( item )
        return rval

    @web.expose_api_anonymous
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
        item = user.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id,
                                                            'total_disk_usage': float } )
        # add a list of tags used by the user (as strings)
        item[ 'tags_used' ] = self.get_user_tags_used( trans, user=user )
        # TODO: move into api_values (needs trans, tho - can we do that with api_keys/@property??)
        # TODO: works with other users (from admin)??
        item['quota_percent'] = trans.app.quota_agent.get_percent( trans=trans )
        item['is_admin'] = trans.user_is_admin()
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
        elif trans.user_is_admin():
            username = payload[ 'username' ]
            email = payload[ 'email' ]
            password = payload[ 'password' ]
            message = "\n".join( [ validate_email( trans, email ),
                                   validate_password( trans, password, password ),
                                   validate_publicname( trans, username ) ] ).rstrip()
            if message:
                raise exceptions.RequestParameterInvalidException( message )
            else:
                user = self.create_user( trans=trans, email=email, username=username, password=password )
        else:
            raise HTTPNotImplemented()
        item = user.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id,
                                                            'total_disk_usage': float } )
        return item

    @web.expose_api
    @web.require_admin
    def api_key( self, trans, user_id, **kwd ):
        """
        POST /api/users/{encoded_user_id}/api_key
        Creates a new API key for specified user.
        """
        user = self.get_user( trans, user_id )
        key = self.create_api_key( trans, user )
        return key

    @web.expose_api
    def update( self, trans, **kwd ):
        raise HTTPNotImplemented()

    @web.expose_api
    def delete( self, trans, **kwd ):
        raise HTTPNotImplemented()

    @web.expose_api
    def undelete( self, trans, **kwd ):
        raise HTTPNotImplemented()

    # TODO: move to more basal, common resource than this
    def anon_user_api_value( self, trans ):
        """
        Returns data for an anonymous user, truncated to only usage and quota_percent
        """
        usage = trans.app.quota_agent.get_usage( trans )
        percent = trans.app.quota_agent.get_percent( trans=trans, usage=usage )
        return {'total_disk_usage': int( usage ),
                'nice_total_disk_usage': util.nice_size( usage ),
                'quota_percent': percent}

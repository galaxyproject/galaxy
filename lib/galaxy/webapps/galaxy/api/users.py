"""
API operations on User objects.
"""

import logging

from sqlalchemy import false, true, or_

from galaxy import exceptions, util, web
from galaxy.managers import users
from galaxy.security.validate_user_input import validate_email
from galaxy.security.validate_user_input import validate_password
from galaxy.security.validate_user_input import validate_publicname
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import CreatesApiKeysMixin
from galaxy.web.base.controller import CreatesUsersMixin
from galaxy.web.base.controller import UsesTagsMixin

log = logging.getLogger( __name__ )


class UserAPIController( BaseAPIController, UsesTagsMixin, CreatesUsersMixin, CreatesApiKeysMixin ):

    def __init__(self, app):
        super(UserAPIController, self).__init__(app)
        self.user_manager = users.UserManager(app)
        self.user_serializer = users.UserSerializer( app )
        self.user_deserializer = users.UserDeserializer( app )

    @expose_api
    def index( self, trans, deleted='False', f_email=None, f_name=None, f_any=None, **kwd ):
        """
        GET /api/users
        GET /api/users/deleted
        Displays a collection (list) of users.

        :param deleted: (optional) If true, show deleted users
        :type  deleted: bool

        :param f_email: (optional) An email address to filter on. (Non-admin
                        users can only use this if ``expose_user_email`` is ``True`` in
                        galaxy.ini)
        :type  f_email: str

        :param f_name: (optional) A username to filter on. (Non-admin users
                       can only use this if ``expose_user_name`` is ``True`` in
                       galaxy.ini)
        :type  f_name: str

        :param f_any: (optional) Filter on username OR email. (Non-admin users
                       can use this, the email filter and username filter will
                       only be active if their corresponding ``expose_user_*`` is
                       ``True`` in galaxy.ini)
        :type  f_any: str
        """
        rval = []
        query = trans.sa_session.query( trans.app.model.User )
        deleted = util.string_as_bool( deleted )

        if f_email and (trans.user_is_admin() or trans.app.config.expose_user_email):
            query = query.filter( trans.app.model.User.email.like("%%%s%%" % f_email) )

        if f_name and (trans.user_is_admin() or trans.app.config.expose_user_name):
            query = query.filter( trans.app.model.User.username.like("%%%s%%" % f_name) )

        if f_any:
            if trans.user_is_admin():
                query = query.filter(or_(
                    trans.app.model.User.email.like("%%%s%%" % f_any),
                    trans.app.model.User.username.like("%%%s%%" % f_any)
                ))
            else:
                if trans.app.config.expose_user_email and trans.app.config.expose_user_name:
                    query = query.filter(or_(
                        trans.app.model.User.email.like("%%%s%%" % f_any),
                        trans.app.model.User.username.like("%%%s%%" % f_any)
                    ))
                elif trans.app.config.expose_user_email:
                    query = query.filter( trans.app.model.User.email.like("%%%s%%" % f_any) )
                elif trans.app.config.expose_user_name:
                    query = query.filter( trans.app.model.User.username.like("%%%s%%" % f_any) )

        if deleted:
            query = query.filter( trans.app.model.User.table.c.deleted == true() )
            # only admins can see deleted users
            if not trans.user_is_admin():
                return []
        else:
            query = query.filter( trans.app.model.User.table.c.deleted == false() )
            # special case: user can see only their own user
            # special case2: if the galaxy admin has specified that other user email/names are
            #   exposed, we don't want special case #1
            if not trans.user_is_admin() and not trans.app.config.expose_user_name and not trans.app.config.expose_user_email:
                item = trans.user.to_dict( value_mapper={ 'id': trans.security.encode_id } )
                return [item]
        for user in query:
            item = user.to_dict( value_mapper={ 'id': trans.security.encode_id } )
            # If NOT configured to expose_email, do not expose email UNLESS the user is self, or
            # the user is an admin
            if not trans.app.config.expose_user_name and user is not trans.user and not trans.user_is_admin():
                del item['username']
            if not trans.app.config.expose_user_email and user is not trans.user and not trans.user_is_admin():
                del item['email']
            # TODO: move into api_values
            rval.append( item )
        return rval

    @expose_api_anonymous
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
            raise exceptions.RequestParameterInvalidException( 'Invalid user id specified', id=id )
        return self.user_serializer.serialize_to_view(user, view='detailed')

    @expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/users
        Creates a new Galaxy user.
        """
        if not trans.app.config.allow_user_creation and not trans.user_is_admin():
            raise exceptions.ConfigDoesNotAllowException( 'User creation is not allowed in this Galaxy instance' )
        if trans.app.config.use_remote_user and trans.user_is_admin():
            user = trans.get_or_create_remote_user( remote_user_email=payload['remote_user_email'] )
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
            raise exceptions.NotImplemented()
        item = user.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id,
                                                            'total_disk_usage': float } )
        return item

    @expose_api
    @web.require_admin
    def api_key( self, trans, user_id, **kwd ):
        """
        POST /api/users/{encoded_user_id}/api_key
        Creates a new API key for specified user.
        """
        user = self.get_user( trans, user_id )
        key = self.create_api_key( trans, user )
        return key

    @expose_api
    def update( self, trans, id, payload, **kwd ):
        """
        update( self, trans, id, payload, **kwd )
        * PUT /api/users/{id}
            updates the values for the item with the given ``id``

        :type id: str
        :param id: the encoded id of the item to update
        :type payload: dict
        :param payload: a dictionary of new attribute values

        :rtype: dict
        :returns: an error object if an error occurred or a dictionary containing
            the serialized item after any changes
        """
        current_user = trans.user
        user_to_update = self.user_manager.by_id( self.decode_id( id ) )

        # only allow updating other users if they're admin
        editing_someone_else = current_user != user_to_update
        is_admin = trans.api_inherit_admin or self.user_manager.is_admin( current_user )
        if editing_someone_else and not is_admin:
            raise exceptions.InsufficientPermissionsException( 'you are not allowed to update that user', id=id )

        self.user_deserializer.deserialize( user_to_update, payload, user=current_user, trans=trans )
        return self.user_serializer.serialize_to_view( user_to_update, view='detailed' )

    @expose_api
    @web.require_admin
    def delete( self, trans, id, **kwd ):
        """
        DELETE /api/users/{id}
        delete the user with the given ``id``

        :param id: the encoded id of the user to delete
        :type  id: str

        :param purge: (optional) if True, purge the user
        :type  purge: bool
        """
        if not trans.app.config.allow_user_deletion:
            raise exceptions.ConfigDoesNotAllowException( 'The configuration of this Galaxy instance does not allow admins to delete users.' )
        purge = util.string_as_bool(kwd.get('purge', False))
        if purge:
            raise exceptions.NotImplemented('Purge option has not been implemented yet')
        user = self.get_user(trans, id)
        self.user_manager.delete(user)
        return self.user_serializer.serialize_to_view(user, view='detailed')

    @expose_api
    @web.require_admin
    def undelete( self, trans, **kwd ):
        raise exceptions.NotImplemented()

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

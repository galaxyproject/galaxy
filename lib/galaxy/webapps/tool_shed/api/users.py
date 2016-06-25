import logging

from galaxy import util
from galaxy import web
from galaxy.web.base.controller import BaseAPIController
from galaxy.security.validate_user_input import validate_email
from galaxy.security.validate_user_input import validate_publicname
from galaxy.security.validate_user_input import validate_password
import tool_shed.util.shed_util_common as suc

log = logging.getLogger( __name__ )


class UsersController( BaseAPIController ):
    """RESTful controller for interactions with users in the Tool Shed."""

    @web.expose_api
    @web.require_admin
    def create( self, trans, payload, **kwd ):
        """
        POST /api/users
        Returns a dictionary of information about the created user.

:       param key: the current Galaxy admin user's API key

        The following parameters are included in the payload.
        :param email (required): the email address of the user
        :param password (required): the password of the user
        :param username (required): the public username of the user
        """
        user_dict = dict( message='',
                          status='ok' )
        # Get the information about the user to be created from the payload.
        email = payload.get( 'email', '' )
        password = payload.get( 'password', '' )
        username = payload.get( 'username', '' )
        message = self.__validate( trans,
                                   email=email,
                                   password=password,
                                   confirm=password,
                                   username=username )
        if message:
            message = 'email: %s, username: %s - %s' % ( email, username, message )
            user_dict[ 'message' ] = message
            user_dict[ 'status' ] = 'error'
        else:
            # Create the user.
            user = self.__create_user( trans, email, username, password )
            user_dict = user.to_dict( view='element',
                                      value_mapper=self.__get_value_mapper( trans ) )
            user_dict[ 'message' ] = "User '%s' has been created." % str( user.username )
            user_dict[ 'url' ] = web.url_for( controller='users',
                                              action='show',
                                              id=trans.security.encode_id( user.id ) )
        return user_dict

    def __create_user( self, trans, email, username, password ):
        user = trans.app.model.User( email=email )
        user.set_password_cleartext( password )
        user.username = username
        if trans.app.config.user_activation_on:
            user.active = False
        else:
            user.active = True  # Activation is off, every new user is active by default.
        trans.sa_session.add( user )
        trans.sa_session.flush()
        trans.app.security_agent.create_private_user_role( user )
        return user

    def __get_value_mapper( self, trans ):
        value_mapper = { 'id' : trans.security.encode_id }
        return value_mapper

    @web.expose_api_anonymous
    def index( self, trans, deleted=False, **kwd ):
        """
        GET /api/users
        Returns a list of dictionaries that contain information about each user.
        """
        # Example URL: http://localhost:9009/api/users
        user_dicts = []
        deleted = util.asbool( deleted )
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted == deleted ) \
                                    .order_by( trans.app.model.User.table.c.username ):
            user_dict = user.to_dict( view='collection',
                                      value_mapper=self.__get_value_mapper( trans ) )
            user_dict[ 'url' ] = web.url_for( controller='users',
                                              action='show',
                                              id=trans.security.encode_id( user.id ) )
            user_dicts.append( user_dict )
        return user_dicts

    @web.expose_api_anonymous
    def show( self, trans, id, **kwd ):
        """
        GET /api/users/{encoded_user_id}
        GET /api/users/current
        Returns a dictionary of information about a user.

        :param id: the encoded id of the User object.
        """
        user = None
        # user is requesting data about themselves
        if id == "current" and trans.user:
            user = trans.user
        else:
            user = suc.get_user( trans.app, id )

        if user is None:
            user_dict = dict( message='Unable to locate user record for id %s.' % ( str( id ) ),
                              status='error' )
            return user_dict
        user_dict = user.to_dict( view='element',
                                  value_mapper=self.__get_value_mapper( trans ) )
        user_dict[ 'url' ] = web.url_for( controller='users',
                                          action='show',
                                          id=trans.security.encode_id( user.id ) )
        return user_dict

    def __validate( self, trans, email, password, confirm, username ):
        if not username:
            return "A public user name is required in the Tool Shed."
        if username in [ 'repos' ]:
            return "The term <b>%s</b> is a reserved word in the Tool Shed, so it cannot be used as a public user name." % username
        message = validate_email( trans, email )
        if not message:
            message = validate_password( trans, password, confirm )
        if not message and username:
            message = validate_publicname( trans, username )
        return message

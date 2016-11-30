from datetime import datetime

from markupsafe import escape

from sqlalchemy import and_
from sqlalchemy import true

from galaxy import util
from galaxy import web

from galaxy.security.validate_user_input import validate_email, validate_password, validate_publicname
from galaxy.web import url_for
from galaxy.webapps.galaxy.controllers.user import User as BaseUser


class User( BaseUser ):

    @web.expose
    def index( self, trans, cntrller='user', **kwd ):
        return trans.fill_template( '/webapps/tool_shed/user/index.mako', cntrller=cntrller )

    @web.expose
    def manage_user_info( self, trans, cntrller, **kwd ):
        '''Manage a user's login, password, public username, type, addresses, etc.'''
        params = util.Params( kwd )
        user_id = params.get( 'id', None )
        if user_id:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
        if not user:
            raise AssertionError("The user id (%s) is not valid" % str( user_id ))
        email = util.restore_text( params.get( 'email', user.email ) )
        username = util.restore_text( params.get( 'username', '' ) )
        if not username:
            username = user.username
        message = escape( util.restore_text( params.get( 'message', ''  ) ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/tool_shed/user/manage_info.mako',
                                    cntrller=cntrller,
                                    user=user,
                                    email=email,
                                    username=username,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login()
    def api_keys( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = escape( util.restore_text( params.get( 'message', ''  ) ) )
        status = params.get( 'status', 'done' )
        if params.get( 'new_api_key_button', False ):
            self.create_api_key( trans, trans.user )
            message = "Generated a new web API key"
            status = "done"
        return trans.fill_template( '/webapps/tool_shed/user/api_keys.mako',
                                    cntrller=cntrller,
                                    user=trans.user,
                                    message=message,
                                    status=status )

    # For REMOTE_USER, we need the ability to just edit the username
    @web.expose
    @web.require_login( "to manage the public name" )
    def edit_username( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        user_id = params.get( 'user_id', None )
        if user_id and is_admin:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
        if user and params.get( 'change_username_button', False ):
            username = kwd.get( 'username', '' )
            if username:
                message = validate_publicname( trans, username, user )
            if message:
                status = 'error'
            else:
                user.username = username
                trans.sa_session.add( user )
                trans.sa_session.flush()
                message = 'The username has been updated with the changes.'
        return trans.fill_template( '/webapps/tool_shed/user/username.mako',
                                    cntrller=cntrller,
                                    user=user,
                                    username=user.username,
                                    message=message,
                                    status=status )

    @web.expose
    def edit_info( self, trans, cntrller, **kwd ):
        """
        Edit user information = username, email or password.
        """
        params = util.Params( kwd )
        is_admin = cntrller == 'admin' and trans.user_is_admin()
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        user_id = params.get( 'user_id', None )
        if user_id and is_admin:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        elif user_id and ( not trans.user or trans.user.id != trans.security.decode_id( user_id ) ):
            message = 'Invalid user id'
            status = 'error'
            user = None
        else:
            user = trans.user
        if user and params.get( 'login_info_button', False ):
            # Editing email and username
            email = util.restore_text( params.get( 'email', '' ) )
            username = util.restore_text( params.get( 'username', '' ) ).lower()

            # Validate the new values for email and username
            message = validate_email( trans, email, user )
            if not message and username:
                message = validate_publicname( trans, username, user )
            if message:
                status = 'error'
            else:
                if ( user.email != email ):
                    # The user's private role name must match the user's login ( email )
                    private_role = trans.app.security_agent.get_private_user_role( user )
                    private_role.name = email
                    private_role.description = 'Private role for ' + email
                    # Change the email itself
                    user.email = email
                    trans.sa_session.add_all( ( user, private_role ) )
                    trans.sa_session.flush()
                    if trans.webapp.name == 'galaxy' and trans.app.config.user_activation_on:
                        user.active = False
                        trans.sa_session.add( user )
                        trans.sa_session.flush()
                        is_activation_sent = self.send_verification_email( trans, user.email, user.username )
                        if is_activation_sent:
                            message = 'The login information has been updated with the changes.<br>Verification email has been sent to your new email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message.'
                        else:
                            message = 'Unable to send activation email, please contact your local Galaxy administrator.'
                            if trans.app.config.error_email_to is not None:
                                message += ' Contact: %s' % trans.app.config.error_email_to
                if ( user.username != username ):
                    user.username = username
                    trans.sa_session.add( user )
                    trans.sa_session.flush()
                message = 'The login information has been updated with the changes.'
        elif user and params.get( 'edit_user_info_button', False ):
            # Edit user information - webapp MUST BE 'galaxy'
            user_type_fd_id = params.get( 'user_type_fd_id', 'none' )
            if user_type_fd_id not in [ 'none' ]:
                user_type_form_definition = trans.sa_session.query( trans.app.model.FormDefinition ).get( trans.security.decode_id( user_type_fd_id ) )
            elif user.values:
                user_type_form_definition = user.values.form_definition
            else:
                # User was created before any of the user_info forms were created
                user_type_form_definition = None
            if user_type_form_definition:
                values = self.get_form_values( trans, user, user_type_form_definition, **kwd )
            else:
                values = {}
            flush_needed = False
            if user.values:
                # Editing the user info of an existing user with existing user info
                user.values.content = values
                trans.sa_session.add( user.values )
                flush_needed = True
            elif values:
                form_values = trans.model.FormValues( user_type_form_definition, values )
                trans.sa_session.add( form_values )
                user.values = form_values
                flush_needed = True
            if flush_needed:
                trans.sa_session.add( user )
                trans.sa_session.flush()
            message = "The user information has been updated with the changes."
        if user and trans.webapp.name == 'galaxy' and is_admin:
            kwd[ 'user_id' ] = trans.security.encode_id( user.id )
        kwd[ 'id' ] = user_id
        if message:
            kwd[ 'message' ] = util.sanitize_text( message )
        if status:
            kwd[ 'status' ] = status
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='manage_user_info',
                                                          cntrller=cntrller,
                                                          **kwd ) )

    @web.expose
    def change_password( self, trans, token=None, **kwd):
        """
        Provides a form with which one can change their password.  If token is
        provided, don't require current password.
        """
        status = None
        message = kwd.get( 'message', '' )
        user = None
        if kwd.get( 'change_password_button', False ):
            password = kwd.get( 'password', '' )
            confirm = kwd.get( 'confirm', '' )
            current = kwd.get( 'current', '' )
            token_result = None
            if token:
                # If a token was supplied, validate and set user
                token_result = trans.sa_session.query( trans.app.model.PasswordResetToken ).get(token)
                if token_result and token_result.expiration_time > datetime.utcnow():
                    user = token_result.user
                else:
                    return trans.show_error_message("Invalid or expired password reset token, please request a new one.")
            else:
                # The user is changing their own password, validate their current password
                (ok, message) = trans.app.auth_manager.check_change_password(trans.user, current )
                if ok:
                    user = trans.user
                else:
                    status = 'error'
            if user:
                # Validate the new password
                message = validate_password( trans, password, confirm )
                if message:
                    status = 'error'
                else:
                    # Save new password
                    user.set_password_cleartext( password )
                    # if we used a token, invalidate it and log the user in.
                    if token_result:
                        trans.handle_user_login(token_result.user)
                        token_result.expiration_time = datetime.utcnow()
                        trans.sa_session.add(token_result)
                    # Invalidate all other sessions
                    for other_galaxy_session in trans.sa_session.query( trans.app.model.GalaxySession ) \
                                                     .filter( and_( trans.app.model.GalaxySession.table.c.user_id == user.id,
                                                                    trans.app.model.GalaxySession.table.c.is_valid == true(),
                                                                    trans.app.model.GalaxySession.table.c.id != trans.galaxy_session.id ) ):
                        other_galaxy_session.is_valid = False
                        trans.sa_session.add( other_galaxy_session )
                    trans.sa_session.add( user )
                    trans.sa_session.flush()
                    trans.log_event( "User change password" )
                    if kwd.get('display_top', False) == 'True':
                        return trans.response.send_redirect( url_for( '/', message='Password has been changed' ))
                    else:
                        return trans.show_ok_message('The password has been changed and any other existing Galaxy sessions have been logged out (but jobs in histories in those sessions will not be interrupted).')
        return trans.fill_template( '/webapps/tool_shed/user/change_password.mako',
                                    token=token,
                                    status=status,
                                    message=message,
                                    display_top=kwd.get('redirect_home', False)
                                    )

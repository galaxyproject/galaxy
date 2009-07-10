"""
Contains the user interface in the Universe class
"""
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy import util
import logging, os, string
from random import choice

log = logging.getLogger( __name__ )

require_login_template = """
<h1>Welcome to Galaxy</h1>

<p>
    This installation of Galaxy has been configured such that only users who are logged in may use it.%s
</p>
<p/>
"""
require_login_nocreation_template = require_login_template % ""
require_login_creation_template = require_login_template % "  If you don't already have an account, <a href='%s'>you may create one</a>."

class User( BaseController ):
    
    @web.expose
    def index( self, trans, **kwd ):
        return trans.fill_template( '/user/index.mako', user=trans.get_user() )
        
    @web.expose
    def change_password(self, trans, old_pass='', new_pass='', conf_pass='', **kwd):
        old_pass_err = new_pass_err = conf_pass_err = ''
        user = trans.get_user()
        if not user:
            trans.response.send_redirect( web.url_for( action='login' ) )
        if trans.request.method == 'POST':
            if not user.check_password( old_pass ):
                old_pass_err = "Invalid password"
            elif len( new_pass ) < 6:
                new_pass_err = "Please use a password of at least 6 characters"
            elif new_pass != conf_pass:
                conf_pass_err = "New passwords do not match."
            else:
                user.set_password_cleartext( new_pass )
                user.flush()
                trans.log_event( "User change password" )
                return trans.show_ok_message( "Password has been changed for " + user.email)
        # Generate input form        
        return trans.show_form( 
            web.FormBuilder( web.url_for() , "Change Password", submit_text="Submit" )
                .add_password( "old_pass", "Old Password", value='', error=old_pass_err )
                .add_password( "new_pass", "New Password", value='', error=new_pass_err ) 
                .add_password( "conf_pass", "Confirm Password", value='', error=conf_pass_err ) )

    @web.expose
    def change_email(self, trans, email='', conf_email='', password='', **kwd):
        email_err = conf_email_err = pass_err = ''
        user = trans.get_user()
        if not user:
            trans.response.send_redirect( web.url_for( action='login' ) )
        if trans.request.method == "POST":
            if not user.check_password( password ):
                pass_err = "Invalid password"
            elif len( email ) == 0 or "@" not in email or "." not in email:
                email_err = "Please enter a real email address"
            elif len( email) > 255:
                email_err = "Email address exceeds maximum allowable length"
            elif trans.app.model.User.filter_by( email=email ).first():
                email_err = "User with that email already exists"
            elif email != conf_email:
                conf_email_err = "Email addresses do not match."
            else:
                user.email = email
                user.flush()
                trans.log_event( "User change email" )
                return trans.show_ok_message( "Email has been changed to: " + user.email, refresh_frames=['masthead', 'history'] )        
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Change Email", submit_text="Submit" )
                .add_text( "email", "Email", value=email, error=email_err )
                .add_text( "conf_email", "Confirm Email", value='', error=conf_email_err ) 
                .add_password( "password", "Password", value='', error=pass_err ) )

    @web.expose
    def login( self, trans, email='', password='' ):
        email_error = password_error = None
        # Attempt login
        if trans.app.config.require_login:
            refresh_frames = [ 'masthead', 'history', 'tools' ]
        else:
            refresh_frames = [ 'masthead', 'history' ]
        if email or password:
            user = trans.app.model.User.filter( trans.app.model.User.table.c.email==email ).first()
            if not user:
                email_error = "No such user"
            elif user.deleted:
                email_error = "This account has been marked deleted, contact your Galaxy administrator to restore the account."
            elif user.external:
                email_error = "This account was created for use with an external authentication method, contact your local Galaxy administrator to activate it."
            elif not user.check_password( password ):
                password_error = "Invalid password"
            else:
                trans.handle_user_login( user )
                trans.log_event( "User logged in" )
                msg = "Now logged in as " + user.email + "."
                if trans.app.config.require_login:
                    msg += '  <a href="%s">Click here</a> to continue to the front page.' % web.url_for( '/static/welcome.html' )
                return trans.show_ok_message( msg, refresh_frames=refresh_frames )
        form = web.FormBuilder( web.url_for(), "Login", submit_text="Login" ) \
                .add_text( "email", "Email address", value=email, error=email_error ) \
                .add_password( "password", "Password", value='', error=password_error, 
                                help="<a href='%s'>Forgot password? Reset here</a>" % web.url_for( action='reset_password' ) )
        if trans.app.config.require_login:
            if trans.app.config.allow_user_creation:
                return trans.show_form( form, header = require_login_creation_template % web.url_for( action = 'create' ) )
            else:
                return trans.show_form( form, header = require_login_nocreation_template )
        else:
            return trans.show_form( form )

    @web.expose
    def logout( self, trans ):
        if trans.app.config.require_login:
            refresh_frames = [ 'masthead', 'history', 'tools' ]
        else:
            refresh_frames = [ 'masthead', 'history' ]
        # Since logging an event requires a session, we'll log prior to ending the session
        trans.log_event( "User logged out" )
        trans.handle_user_logout()
        msg = "You are no longer logged in."
        if trans.app.config.require_login:
            msg += '  <a href="%s">Click here</a> to return to the login page.' % web.url_for( controller='user', action='login' )
        return trans.show_ok_message( msg, refresh_frames=refresh_frames )

    @web.expose
    def create( self, trans, email='', password='', confirm='', subscribe=False ):
        if trans.app.config.require_login:
            refresh_frames = [ 'masthead', 'history', 'tools' ]
        else:
            refresh_frames = [ 'masthead', 'history' ]
        if not trans.app.config.allow_user_creation and not trans.user_is_admin():
            return trans.show_error_message( 'User registration is disabled.  Please contact your Galaxy administrator for an account.' )
        email_error = password_error = confirm_error = None
        if email:
            if len( email ) == 0 or "@" not in email or "." not in email:
                email_error = "Please enter a real email address"
            elif len( email ) > 255:
                email_error = "Email address exceeds maximum allowable length"
            elif trans.app.model.User.filter( and_( trans.app.model.User.table.c.email==email,
                                                    trans.app.model.User.table.c.deleted==False ) ).first():
                email_error = "User with that email already exists"
            elif len( password ) < 6:
                password_error = "Please use a password of at least 6 characters"
            elif password != confirm:
                confirm_error = "Passwords do not match"
            else:
                user = trans.app.model.User( email=email )
                user.set_password_cleartext( password )
                user.flush()
                trans.app.security_agent.create_private_user_role( user )
                # We set default user permissions, before we log in and set the default history permissions
                trans.app.security_agent.user_set_default_permissions( user )
                # The handle_user_login() method has a call to the history_set_default_permissions() method
                # (needed when logging in with a history), user needs to have default permissions set before logging in
                trans.handle_user_login( user )
                trans.log_event( "User created a new account" )
                trans.log_event( "User logged in" )
                #subscribe user to email list
                if subscribe:
                    mail = os.popen("%s -t" % trans.app.config.sendmail_path, 'w')
                    mail.write("To: %s\nFrom: %s\nSubject: Join Mailing List\n\nJoin Mailing list." % (trans.app.config.mailing_join_addr,email) )
                    if mail.close():
                        return trans.show_warn_message( "Now logged in as " + user.email+". However, subscribing to the mailing list has failed.", refresh_frames=refresh_frames )
                return trans.show_ok_message( "Now logged in as " + user.email, refresh_frames=refresh_frames )
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Create account", submit_text="Create" )
                .add_text( "email", "Email address", value=email, error=email_error )
                .add_password( "password", "Password", value='', error=password_error ) 
                .add_password( "confirm", "Confirm password", value='', error=confirm_error ) 
                .add_input( "checkbox","Subscribe To Mailing List","subscribe", value='subscribe' ) )

    @web.expose
    def reset_password( self, trans, email=None, **kwd ):
        error = ''
        reset_user = trans.app.model.User.filter( trans.app.model.User.table.c.email==email ).first()
        user = trans.get_user()
        if reset_user:
            if user and user.id != reset_user.id:
                error = "You may only reset your own password"
            else:
                chars = string.letters + string.digits
                new_pass = ""
                for i in range(15):
                    new_pass = new_pass + choice(chars)
                mail = os.popen("%s -t" % trans.app.config.sendmail_path, 'w')
                mail.write("To: %s\nFrom: no-reply@%s\nSubject: Galaxy Password Reset\n\nYour password has been reset to \"%s\" (no quotes)." % (email, trans.request.remote_addr, new_pass) )
                if mail.close():
                    return trans.show_error_message( 'Failed to reset password.  If this problem persists, please submit a bug report.' )
                reset_user.set_password_cleartext( new_pass )
                reset_user.flush()
                trans.log_event( "User reset password: %s" % email )
                return trans.show_ok_message( "Password has been reset and emailed to: %s.  <a href='%s'>Click here</a> to return to the login form." % ( email, web.url_for( action='login' ) ) )
        elif email != None:
            error = "The specified user does not exist"
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Reset Password", submit_text="Submit" )
                .add_text( "email", "Email", value=email, error=error ) )
    
    @web.expose
    def set_default_permissions( self, trans, **kwd ):
        """Sets the user's default permissions for the new histories"""
        if trans.user:
            if 'update_roles_button' in kwd:
                p = util.Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = p.get( k + '_in', [] )
                    if not isinstance( in_roles, list ):
                        in_roles = [ in_roles ]
                    in_roles = [ trans.app.model.Role.get( x ) for x in in_roles ]
                    action = trans.app.security_agent.get_action( v.action ).action
                    permissions[ action ] = in_roles
                trans.app.security_agent.user_set_default_permissions( trans.user, permissions )
                return trans.show_ok_message( 'Default new history permissions have been changed.' )
            return trans.fill_template( 'user/permissions.mako' )
        else:
            # User not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change your default permitted actions." )

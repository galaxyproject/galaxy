"""
Contains the user interface in the Universe class
"""
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy import util
import logging, os, string
from random import choice

log = logging.getLogger( __name__ )

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
        if email or password:
            user = trans.app.model.User.filter_by( email=email ).first()
            if not user:
                email_error = "No such user"
            elif user.external:
                return trans.show_error_message( "This account was created for use with an external authentication "
                                               + "method.  Please contact your local Galaxy administrator to activate it." )
            elif not user.check_password( password ):
                password_error = "Invalid password"
            else:
                trans.handle_user_login( user )
                trans.log_event( "User logged in" )
                return trans.show_ok_message( "Now logged in as " + user.email, refresh_frames=['masthead', 'history'] )
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Login", submit_text="Login" )
                .add_text( "email", "Email address", value=email, error=email_error )
                .add_password( "password", "Password", value='', error=password_error, 
                                help="<a href='%s'>Forgot password? Reset here</a>" % web.url_for( action='reset_password' ) ) )
    @web.expose
    def logout( self, trans ):
        # Since logging an event requires a session, we'll log prior to ending the session
        trans.log_event( "User logged out" )
        trans.handle_user_logout()
        return trans.show_ok_message( "You are no longer logged in", refresh_frames=['masthead', 'history'] )
            
    @web.expose
    def create( self, trans, email='', password='', confirm='',subscribe=False ):
        email_error = password_error = confirm_error = None
        if email:
            if len( email ) == 0 or "@" not in email or "." not in email:
                email_error = "Please enter a real email address"
            elif len( email) > 255:
                email_error = "Email address exceeds maximum allowable length"
            elif trans.app.model.User.filter_by( email=email ).first():
                email_error = "User with that email already exists"
            elif len( password ) < 6:
                password_error = "Please use a password of at least 6 characters"
            elif password != confirm:
                confirm_error = "Passwords do not match"
            else:
                user = trans.app.model.User( email=email )
                user.set_password_cleartext( password )
                user.flush()
                trans.handle_user_login( user )
                trans.log_event( "User created a new account" )
                trans.log_event( "User logged in" )
                #subscribe user to email list
                if subscribe:
                    mail = os.popen("%s -t" % self.app.config.sendmail_path, 'w')
                    mail.write("To: %s\nFrom: %s\nSubject: Join Mailing List\n\nJoin Mailing list." % (self.app.config.mailing_join_addr,email) )
                    if mail.close():
                        return trans.show_warn_message( "Now logged in as " + user.email+". However, subscribing to the mailing list has failed.", refresh_frames=['masthead', 'history'] )
                return trans.show_ok_message( "Now logged in as " + user.email, refresh_frames=['masthead', 'history'] )
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Create account", submit_text="Create" )
                .add_text( "email", "Email address", value=email, error=email_error )
                .add_password( "password", "Password", value='', error=password_error ) 
                .add_password( "confirm", "Confirm password", value='', error=confirm_error ) 
                .add_input( "checkbox","Subscribe To Mailing List","subscribe", value='subscribe' ) )

    @web.expose
    def reset_password(self, trans, email=None, **kwd):
        error = ''
        reset_user = trans.app.model.User.filter_by( email=email ).first()
        user = trans.get_user()
        if reset_user:
            if user and user.id != reset_user.id:
                    error = "You may only reset your own password"
            else:
                chars = string.letters + string.digits
                new_pass = ""
                for i in range(15):
                    new_pass = new_pass + choice(chars)
                mail = os.popen("%s -t" % self.app.config.sendmail_path, 'w')
                mail.write("To: %s\nFrom: no-reply@%s\nSubject: Galaxy Password Reset\n\nYour password has been reset to \"%s\" (no quotes)." % (email, trans.request.remote_addr, new_pass) )
                if mail.close():
                    return trans.show_ok_message( "Failed to reset password! If this problem persist, submit a bug report.")
                reset_user.set_password_cleartext( new_pass )
                reset_user.flush()
                trans.log_event( "User reset password: %s" % email )
                return trans.show_ok_message( "Password has been reset and emailed to: %s." % email)
        elif email != None:
            error = "The specified user does not exist"
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Reset Password", submit_text="Submit" )
                .add_text( "email", "Email", value=email, error=error ) )
    
    @web.expose
    def set_default_permissions( self, trans, **kwd ):
        """Sets the user's default permissions for the new histories"""
        if trans.user:
            if 'update_roles' in kwd:
                p = util.Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = p.get( k + '_in', [] )
                    if not isinstance( in_roles, list ):
                        in_roles = [ in_roles ]
                    in_roles = [ trans.app.model.Role.get( x ) for x in in_roles ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.user_set_default_permissions( trans.user, permissions )
                return trans.show_ok_message( 'Default new history permissions have been changed.' )
            return trans.fill_template( 'user/permissions.mako' )
        else:
            # User not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change your default permitted actions." )

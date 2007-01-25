"""
Contains the user interface in the Universe class
"""
import logging, common, os, string
from random import choice
from galaxy import web, config

log = logging.getLogger( __name__ )

class User( common.Root ):
    @web.expose
    def index( self, trans, **kwd ):
        if trans.get_user():
            trans.response.send_redirect("/user/account")
        return trans.fill_template('user_main.tmpl')
        
    @web.expose
    def account( self, trans, **kwd ):
        msg = ''
        user = trans.get_user()
        if not user:
            trans.response.send_redirect("/user/login")
        return trans.fill_template('user_account.tmpl', user=user, history=trans.get_history(), msg=msg)

    @web.expose
    def change_password(self, trans, old_pass='', new_pass='', conf_pass='', **kwd):
        old_pass_err = new_pass_err = conf_pass_err = ''
        user = trans.get_user()
        if not user:
            trans.response.send_redirect("/user/login")
        
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
        
        return trans.show_form( 
            web.FormBuilder( "/user/change_password", "Change Password", submit_text="Submit" )
                .add_password( "old_pass", "Old Password", value='', error=old_pass_err )
                .add_password( "new_pass", "New Password", value='', error=new_pass_err ) 
                .add_password( "conf_pass", "Confirm Password", value='', error=conf_pass_err ) )

    @web.expose
    def change_email(self, trans, email='', conf_email='', password='', **kwd):
        email_err = conf_email_err = pass_err = ''
        user = trans.get_user()
        if not user:
            trans.response.send_redirect("/user/login")
        
        if not user.check_password( password ):
            pass_err = "Invalid password"
        elif len( email ) == 0 or "@" not in email or "." not in email:
            email_err = "Please enter a real email address"
        elif len( email) > 255:
            email_err = "Email address exceeds maximum allowable length"
        elif len( trans.app.model.User.select_by( email=email ) ) > 0:
            email_err = "User with that email already exists"
        elif email != conf_email:
            conf_email_err = "Email addresses do not match."
        else:
            user.email = email
            user.flush()
            trans.log_event( "User change email" )
            return trans.show_ok_message( "Email has been changed to: " + user.email, refresh_frames=['masthead', 'history'] )
        
        return trans.show_form( 
            web.FormBuilder( "/user/change_email", "Change Email", submit_text="Submit" )
                .add_text( "email", "Email", value=email, error=email_err )
                .add_text( "conf_email", "Confirm Email", value='', error=conf_email_err ) 
                .add_password( "password", "Password", value='', error=pass_err ) )

    @web.expose
    def login( self, trans, email='', password='' ):
        email_error = password_error = None
        # Attempt login
        if email or password:
            user = trans.app.model.User.get_by( email = email )
            if not user:
                email_error = "No such user"
            elif not user.check_password( password ):
                password_error = "Invalid password"
            else:
                trans.set_user( user )
                trans.ensure_valid_galaxy_session()
                """
                Associate user with galaxy_session and history
                """
                trans.make_associations()
                trans.log_event( "User logged in" )
                return trans.show_ok_message( "Now logged in as " + user.email, \
                    refresh_frames=['masthead', 'history'] )
        return trans.show_form( 
            web.FormBuilder( "/user/login", "Login", submit_text="Login" )
                .add_text( "email", "Email address", value=email, error=email_error )
                .add_password( "password", "Password", value='', error=password_error, help="<a href=\"/user/reset_password\">Forgot password? Reset here</a>" ) )

    @web.expose
    def logout( self, trans ):
        trans.log_event( "User logged out" )
        # If the current history is saved for the current user it should be disconnected.
        if trans.history.user == trans.user:
            trans.set_history( None )
        trans.set_user( None )
        trans.end_galaxy_session()
        return trans.show_ok_message( "You are no longer logged in", \
            refresh_frames=['masthead', 'history'] )
            
    @web.expose
    def create( self, trans, email='', password='', confirm='',subscribe=False ):
        email_error = password_error = confirm_error = None
        if email:
            if len( email ) == 0 or "@" not in email or "." not in email:
                email_error = "Please enter a real email address"
            elif len( email) > 255:
                email_error = "Email address exceeds maximum allowable length"
            elif len( trans.app.model.User.select_by( email=email ) ) > 0:
                email_error = "User with that email already exists"
            elif len( password ) < 6:
                password_error = "Please use a password of at least 6 characters"
            elif password != confirm:
                confirm_error = "Passwords do not match"
            else:
                user = trans.app.model.User( email=email )
                user.set_password_cleartext( password )
                user.flush()
                trans.set_user( user )
                trans.ensure_valid_galaxy_session()
                """
                Associate user with galaxy_session and history
                """
                trans.make_associations()
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
            web.FormBuilder( "/user/create", "Create account", submit_text="Create" )
                .add_text( "email", "Email address", value=email, error=email_error )
                .add_password( "password", "Password", value='', error=password_error ) 
                .add_password( "confirm", "Confirm password", value='', error=confirm_error ) 
                .add_input( "checkbox","Subscribe To Mailing List","subscribe", value='subscribe' ) )

    @web.expose
    def reset_password(self, trans, email=None, **kwd):
        error = ''
        reset_user = trans.app.model.User.get_by( email = email )
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
            web.FormBuilder( "/user/reset_password", "Reset Password", submit_text="Submit" )
                .add_text( "email", "Email", value=email, error=error ) )
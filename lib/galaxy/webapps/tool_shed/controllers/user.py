import logging
import socket

from markupsafe import escape
from sqlalchemy import func

from galaxy import (
    util,
    web
)
from galaxy.security.validate_user_input import (
    transform_publicname,
    validate_email,
    validate_publicname
)
from galaxy.web import url_for
from galaxy.web.form_builder import CheckboxField
from galaxy.webapps.galaxy.controllers.user import User as BaseUser

log = logging.getLogger(__name__)

REQUIRE_LOGIN_TEMPLATE = """
<p>
    This %s has been configured such that only users who are logged in may use it.%s
</p>
"""

PASSWORD_RESET_TEMPLATE = """
To reset your Galaxy password for the instance at %s use the following link,
which will expire %s.

%s

If you did not make this request, no action is necessary on your part, though
you may want to notify an administrator.

If you're having trouble using the link when clicking it from email client, you
can also copy and paste it into your browser.
"""


class User(BaseUser):

    @web.expose
    def index(self, trans, cntrller='user', **kwd):
        return trans.fill_template('/webapps/tool_shed/user/index.mako', cntrller=cntrller)

    @web.expose
    def login(self, trans, refresh_frames=[], **kwd):
        '''Handle Galaxy Log in'''
        referer = trans.request.referer or ''
        redirect = self.__get_redirect_url(kwd.get('redirect', referer).strip())
        redirect_url = ''  # always start with redirect_url being empty
        use_panels = util.string_as_bool(kwd.get('use_panels', False))
        message = kwd.get('message', '')
        status = kwd.get('status', 'done')
        header = ''
        user = trans.user
        success = False
        login = kwd.get('login', '')
        if user:
            # Already logged in.
            redirect_url = redirect
            message = 'You are already logged in.'
            status = 'info'
        elif kwd.get('login_button', False):
            response = self.__validate_login(trans, **kwd)
            if trans.response.status == 400:
                trans.response.status = 200
                message = response.get("err_msg")
                status = "error"
            elif response.get("expired_user"):
                change_password_url = url_for(controller='user', action='change_password', id=response.get("expired_user"))
                message = "%s<br>Click <a href='%s'>here</a> to change your password." % (response.get("message"), change_password_url)
                status = "warning"
            else:
                success = True
            if success:
                redirect_url = redirect
        if not success and not user and trans.app.config.require_login:
            if trans.app.config.allow_user_creation:
                create_account_str = "  If you don't already have an account, <a href='%s'>you may create one</a>." % \
                    web.url_for(controller='user', action='create', cntrller='user')
                header = REQUIRE_LOGIN_TEMPLATE % ("Galaxy tool shed", create_account_str)
            else:
                header = REQUIRE_LOGIN_TEMPLATE % ("Galaxy tool shed", "")
        return trans.fill_template('/webapps/tool_shed/user/login.mako',
                                   login=login,
                                   header=header,
                                   use_panels=use_panels,
                                   redirect_url=redirect_url,
                                   redirect=redirect,
                                   refresh_frames=refresh_frames,
                                   message=message,
                                   status=status,
                                   form_input_auto_focus=True,
                                   active_view="user")

    @web.expose
    def create(self, trans, cntrller='user', redirect_url='', refresh_frames=[], **kwd):
        params = util.Params(kwd)
        # If the honeypot field is not empty we are dealing with a bot.
        honeypot_field = params.get('bear_field', '')
        if honeypot_field != '':
            return trans.show_error_message("You've been flagged as a possible bot. If you are not, please try registering again and fill the form out carefully. <a target=\"_top\" href=\"%s\">Go to the home page</a>.") % url_for('/')

        message = util.restore_text(params.get('message', ''))
        status = params.get('status', 'done')
        use_panels = util.string_as_bool(kwd.get('use_panels', True))
        email = util.restore_text(params.get('email', ''))
        # Do not sanitize passwords, so take from kwd
        # instead of params ( which were sanitized )
        password = kwd.get('password', '')
        confirm = kwd.get('confirm', '')
        username = util.restore_text(params.get('username', ''))
        subscribe = params.get('subscribe', '')
        subscribe_checked = CheckboxField.is_checked(subscribe)
        referer = trans.request.referer or ''
        redirect = kwd.get('redirect', referer).strip()
        is_admin = trans.user_is_admin
        success = False
        show_user_prepopulate_form = False
        if not trans.app.config.allow_user_creation and not trans.user_is_admin:
            message = 'User registration is disabled.  Please contact your local Galaxy administrator for an account.'
            if trans.app.config.error_email_to is not None:
                message += ' Contact: %s' % trans.app.config.error_email_to
            status = 'error'
        else:
            # check user is allowed to register
            message, status = trans.app.auth_manager.check_registration_allowed(email, username, password)
            if not message:
                # Create the user, save all the user info and login to Galaxy
                if params.get('create_user_button', False):
                    # Check email and password validity
                    message = self.__validate(trans, email, password, confirm, username)
                    if not message:
                        # All the values are valid
                        message, status, user, success = self.__register(trans, subscribe_checked=subscribe_checked, **kwd)
                        if success and not is_admin:
                            # The handle_user_login() method has a call to the history_set_default_permissions() method
                            # (needed when logging in with a history), user needs to have default permissions set before logging in
                            trans.handle_user_login(user)
                            trans.log_event("User created a new account")
                            trans.log_event("User logged in")
                    else:
                        status = 'error'
        registration_warning_message = trans.app.config.registration_warning_message
        if success:
            if is_admin:
                redirect_url = web.url_for('/admin/users?status=success&message=Created new user account.')
            else:
                redirect_url = web.url_for('/')
        return trans.fill_template('/webapps/tool_shed/user/register.mako',
                                   cntrller=cntrller,
                                   email=email,
                                   username=transform_publicname(trans, username),
                                   subscribe_checked=subscribe_checked,
                                   show_user_prepopulate_form=show_user_prepopulate_form,
                                   use_panels=use_panels,
                                   redirect=redirect,
                                   redirect_url=redirect_url,
                                   refresh_frames=refresh_frames,
                                   registration_warning_message=registration_warning_message,
                                   message=message,
                                   status=status)

    def __register(self, trans, email=None, username=None, password=None, subscribe_checked=False, **kwd):
        """Registers a new user."""
        email = util.restore_text(email)
        username = util.restore_text(username)
        status = None
        message = None
        is_admin = trans.user_is_admin
        user = self.user_manager.create(email=email, username=username, password=password)
        if subscribe_checked:
            # subscribe user to email list
            if trans.app.config.smtp_server is None:
                status = "error"
                message = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed because mail is not configured for this Galaxy instance. <br>Please contact your local Galaxy administrator."
            else:
                body = 'Join Mailing list.\n'
                to = trans.app.config.mailing_join_addr
                frm = email
                subject = 'Join Mailing List'
                try:
                    util.send_mail(frm, to, subject, body, trans.app.config)
                except Exception:
                    log.exception('Subscribing to the mailing list has failed.')
                    status = "warning"
                    message = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed."
        if status != "error":
            if not is_admin:
                # The handle_user_login() method has a call to the history_set_default_permissions() method
                # (needed when logging in with a history), user needs to have default permissions set before logging in
                trans.handle_user_login(user)
                trans.log_event("User created a new account")
                trans.log_event("User logged in")
            if trans.app.config.user_activation_on:
                is_activation_sent = self.user_manager.send_activation_email(trans, email, username)
                if is_activation_sent:
                    message = 'Now logged in as %s.<br>Verification email has been sent to your email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message.<br><a target="_top" href="%s">Return to the home page.</a>' % (escape(user.email), url_for('/'))
                else:
                    status = "error"
                    message = 'Unable to send activation email, please contact your local Galaxy administrator.'
                    if trans.app.config.error_email_to is not None:
                        message += ' Contact: %s' % trans.app.config.error_email_to
        else:
            # User activation is OFF, proceed without sending the activation email.
            message = 'Now logged in as %s.<br><a target="_top" href="%s">Return to the home page.</a>' % (escape(user.email), url_for('/'))
        return message, status, user, status is None

    @web.expose
    def reset_password(self, trans, email=None, **kwd):
        """Reset the user's password. Send an email with token that allows a password change."""
        if trans.app.config.smtp_server is None:
            return trans.show_error_message("Mail is not configured for this Galaxy instance "
                                            "and password reset information cannot be sent. "
                                            "Please contact your local Galaxy administrator.")
        message = None
        status = 'done'
        if kwd.get('reset_password_button', False):
            message = validate_email(trans, email, check_dup=False)
            if not message:
                # Default to a non-userinfo-leaking response message
                message = ("Your reset request for %s has been received.  "
                           "Please check your email account for more instructions.  "
                           "If you do not receive an email shortly, please contact an administrator." % (escape(email)))
                reset_user = trans.sa_session.query(trans.app.model.User).filter(trans.app.model.User.table.c.email == email).first()
                if not reset_user:
                    # Perform a case-insensitive check only if the user wasn't found
                    reset_user = trans.sa_session.query(trans.app.model.User).filter(func.lower(trans.app.model.User.table.c.email) == func.lower(email)).first()
                if reset_user:
                    prt = trans.app.model.PasswordResetToken(reset_user)
                    trans.sa_session.add(prt)
                    trans.sa_session.flush()
                    host = trans.request.host.split(':')[0]
                    if host in ['localhost', '127.0.0.1', '0.0.0.0']:
                        host = socket.getfqdn()
                    reset_url = url_for(controller='user',
                                        action="change_password",
                                        token=prt.token, qualified=True)
                    body = PASSWORD_RESET_TEMPLATE % (host, prt.expiration_time.strftime(trans.app.config.pretty_datetime_format),
                                                      reset_url)
                    frm = trans.app.config.email_from or 'galaxy-no-reply@' + host
                    subject = 'Galaxy Password Reset'
                    try:
                        util.send_mail(frm, email, subject, body, trans.app.config)
                        trans.sa_session.add(reset_user)
                        trans.sa_session.flush()
                        trans.log_event("User reset password: %s" % email)
                    except Exception:
                        log.exception('Unable to reset password.')
        return trans.fill_template('/webapps/tool_shed/user/reset_password.mako',
                                   message=message,
                                   status=status)

    @web.expose
    def manage_user_info(self, trans, cntrller, **kwd):
        '''Manage a user's login, password, public username, type, addresses, etc.'''
        params = util.Params(kwd)
        user_id = params.get('id', None)
        if user_id:
            user = trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(user_id))
        else:
            user = trans.user
        if not user:
            raise AssertionError("The user id (%s) is not valid" % str(user_id))
        email = util.restore_text(params.get('email', user.email))
        username = util.restore_text(params.get('username', ''))
        if not username:
            username = user.username
        message = escape(util.restore_text(params.get('message', '')))
        status = params.get('status', 'done')
        return trans.fill_template('/webapps/tool_shed/user/manage_info.mako',
                                   cntrller=cntrller,
                                   user=user,
                                   email=email,
                                   username=username,
                                   message=message,
                                   status=status)

    @web.expose
    @web.require_login()
    def api_keys(self, trans, cntrller, **kwd):
        params = util.Params(kwd)
        message = escape(util.restore_text(params.get('message', '')))
        status = params.get('status', 'done')
        if params.get('new_api_key_button', False):
            self.create_api_key(trans, trans.user)
            message = "Generated a new web API key"
            status = "done"
        return trans.fill_template('/webapps/tool_shed/user/api_keys.mako',
                                   cntrller=cntrller,
                                   user=trans.user,
                                   message=message,
                                   status=status)

    # For REMOTE_USER, we need the ability to just edit the username
    @web.expose
    @web.require_login("to manage the public name")
    def edit_username(self, trans, cntrller, **kwd):
        params = util.Params(kwd)
        is_admin = cntrller == 'admin' and trans.user_is_admin
        message = util.restore_text(params.get('message', ''))
        status = params.get('status', 'done')
        user_id = params.get('user_id', None)
        if user_id and is_admin:
            user = trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(user_id))
        else:
            user = trans.user
        if user and params.get('change_username_button', False):
            username = kwd.get('username', '')
            if username:
                message = validate_publicname(trans, username, user)
            if message:
                status = 'error'
            else:
                user.username = username
                trans.sa_session.add(user)
                trans.sa_session.flush()
                message = 'The username has been updated with the changes.'
        return trans.fill_template('/webapps/tool_shed/user/username.mako',
                                   cntrller=cntrller,
                                   user=user,
                                   username=user.username,
                                   message=message,
                                   status=status)

    @web.expose
    def edit_info(self, trans, cntrller, **kwd):
        """
        Edit user information = username, email or password.
        """
        params = util.Params(kwd)
        is_admin = cntrller == 'admin' and trans.user_is_admin
        message = util.restore_text(params.get('message', ''))
        status = params.get('status', 'done')
        user_id = params.get('user_id', None)
        if user_id and is_admin:
            user = trans.sa_session.query(trans.app.model.User).get(trans.security.decode_id(user_id))
        elif user_id and (not trans.user or trans.user.id != trans.security.decode_id(user_id)):
            message = 'Invalid user id'
            status = 'error'
            user = None
        else:
            user = trans.user
        if user and params.get('login_info_button', False):
            # Editing email and username
            email = util.restore_text(params.get('email', ''))
            username = util.restore_text(params.get('username', '')).lower()

            # Validate the new values for email and username
            message = validate_email(trans, email, user)
            if not message and username:
                message = validate_publicname(trans, username, user)
            if message:
                status = 'error'
            else:
                if (user.email != email):
                    # The user's private role name must match the user's login ( email )
                    private_role = trans.app.security_agent.get_private_user_role(user)
                    private_role.name = email
                    private_role.description = 'Private role for ' + email
                    # Change the email itself
                    user.email = email
                    trans.sa_session.add_all((user, private_role))
                    trans.sa_session.flush()
                    if trans.webapp.name == 'galaxy' and trans.app.config.user_activation_on:
                        user.active = False
                        trans.sa_session.add(user)
                        trans.sa_session.flush()
                        is_activation_sent = self.user_manager.send_activation_email(trans, user.email, user.username)
                        if is_activation_sent:
                            message = 'The login information has been updated with the changes.<br>Verification email has been sent to your new email address. Please verify it by clicking the activation link in the email.<br>Please check your spam/trash folder in case you cannot find the message.'
                        else:
                            message = 'Unable to send activation email, please contact your local Galaxy administrator.'
                            if trans.app.config.error_email_to is not None:
                                message += ' Contact: %s' % trans.app.config.error_email_to
                if (user.username != username):
                    user.username = username
                    trans.sa_session.add(user)
                    trans.sa_session.flush()
                message = 'The login information has been updated with the changes.'
        elif user and params.get('edit_user_info_button', False):
            # Edit user information - webapp MUST BE 'galaxy'
            user_type_fd_id = params.get('user_type_fd_id', 'none')
            if user_type_fd_id not in ['none']:
                user_type_form_definition = trans.sa_session.query(trans.app.model.FormDefinition).get(trans.security.decode_id(user_type_fd_id))
            elif user.values:
                user_type_form_definition = user.values.form_definition
            else:
                # User was created before any of the user_info forms were created
                user_type_form_definition = None
            if user_type_form_definition:
                values = self.get_form_values(trans, user, user_type_form_definition, **kwd)
            else:
                values = {}
            flush_needed = False
            if user.values:
                # Editing the user info of an existing user with existing user info
                user.values.content = values
                trans.sa_session.add(user.values)
                flush_needed = True
            elif values:
                form_values = trans.model.FormValues(user_type_form_definition, values)
                trans.sa_session.add(form_values)
                user.values = form_values
                flush_needed = True
            if flush_needed:
                trans.sa_session.add(user)
                trans.sa_session.flush()
            message = "The user information has been updated with the changes."
        if user and trans.webapp.name == 'galaxy' and is_admin:
            kwd['user_id'] = trans.security.encode_id(user.id)
        kwd['id'] = user_id
        if message:
            kwd['message'] = util.sanitize_text(message)
        if status:
            kwd['status'] = status
        return trans.response.send_redirect(web.url_for(controller='user',
                                                        action='manage_user_info',
                                                        cntrller=cntrller,
                                                        **kwd))

    @web.expose
    def change_password(self, trans, token=None, id=None, **kwd):
        """
        Provides a form with which one can change their password.  If token is
        provided, don't require current password.
        """
        if kwd.get('change_password_button', False):
            password = kwd.get('password', '')
            confirm = kwd.get('confirm', '')
            current = kwd.get('current', '')
            user, message = self.user_manager.change_password(trans, password=password,
                current=current, token=token, confirm=confirm, id=id)
            if not user:
                return trans.show_error_message(message)
            return trans.show_ok_message('The password has been changed and any other existing Galaxy sessions have been logged out (but jobs in histories in those sessions will not be interrupted).')
        return trans.fill_template('/webapps/tool_shed/user/change_password.mako', token=token, id=id)

    @web.expose
    def logout(self, trans, logout_all=False, **kwd):
        trans.handle_user_logout(logout_all=logout_all)
        message = 'You have been logged out.<br>To log in again <a target="_top" href="%s">go to the home page</a>.' % \
            (url_for('/'))
        if trans.app.config.use_remote_user and trans.app.config.remote_user_logout_href:
            trans.response.send_redirect(trans.app.config.remote_user_logout_href)
        else:
            return trans.fill_template('/webapps/tool_shed/user/logout.mako',
                                       refresh_frames=['masthead'],
                                       message=message,
                                       status='done',
                                       active_view="user")

    def __validate(self, trans, email, password, confirm, username):
        # If coming from the tool shed webapp, we'll require a public user name
        if not username:
            return "A public user name is required in the tool shed."
        if username in ['repos']:
            return "The term <b>%s</b> is a reserved word in the tool shed, so it cannot be used as a public user name." % escape(username)
        return super(User, self).__validate(trans, email, password, confirm, username)

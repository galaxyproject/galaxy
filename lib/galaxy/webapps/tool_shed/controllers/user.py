import logging
import socket

from markupsafe import escape
from sqlalchemy import func

from galaxy import (
    util,
    web
)
from galaxy.security.validate_user_input import (
    validate_email,
    validate_publicname
)
from galaxy.web import url_for
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
            csrf_check = trans.check_csrf_token()
            if csrf_check:
                return csrf_check
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
                                   openid_providers=trans.app.openid_providers,
                                   form_input_auto_focus=True,
                                   active_view="user")

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
        is_admin = cntrller == 'admin' and trans.user_is_admin()
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
        is_admin = cntrller == 'admin' and trans.user_is_admin()
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

    def __validate(self, trans, email, password, confirm, username):
        # If coming from the tool shed webapp, we'll require a public user name
        if not username:
            return "A public user name is required in the tool shed."
        if username in ['repos']:
            return "The term <b>%s</b> is a reserved word in the tool shed, so it cannot be used as a public user name." % escape(username)
        return super(User, self).__validate(trans, email, password, confirm, username)

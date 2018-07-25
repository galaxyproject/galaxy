"""
Contains the user interface in the Universe class
"""

import logging
from datetime import datetime, timedelta

from markupsafe import escape
from six.moves.urllib.parse import unquote
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound

from galaxy import (
    model,
    util,
    web
)
from galaxy.managers import users
from galaxy.queue_worker import send_local_control_task
from galaxy.security.validate_user_input import (
    transform_publicname,
    validate_email,
    validate_password,
    validate_publicname
)
from galaxy.util import biostar
from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web import url_for
from galaxy.web.base.controller import (
    BaseUIController,
    CreatesApiKeysMixin,
    UsesFormDefinitionsMixin
)
from galaxy.web.form_builder import CheckboxField
from galaxy.web.framework.helpers import grids, time_ago

log = logging.getLogger(__name__)


class UserOpenIDGrid(grids.Grid):
    title = "OpenIDs linked to your account"
    model_class = model.UserOpenID
    default_filter = {"openid": "All"}
    default_sort_key = "-create_time"
    columns = [
        grids.TextColumn("OpenID URL", key="openid"),
        grids.GridColumn("Created", key="create_time", format=time_ago),
    ]
    global_actions = [
        grids.GridAction("Add new account", url_args=dict(action="create_openid"), target="center")
    ]
    operations = [
        grids.GridOperation("Delete", async_compatible=True),
    ]

    def build_initial_query(self, trans, **kwd):
        return trans.sa_session.query(self.model_class).filter(self.model_class.user_id == trans.user.id)


class User(BaseUIController, UsesFormDefinitionsMixin, CreatesApiKeysMixin):
    user_openid_grid = UserOpenIDGrid()
    installed_len_files = None

    def __init__(self, app):
        super(User, self).__init__(app)
        self.user_manager = users.UserManager(app)

    @web.expose
    def openid_process(self, trans, **kwd):
        '''Handle's response from OpenID Providers'''
        if not trans.app.config.enable_openid:
            return trans.show_error_message('OpenID authentication is not enabled in this instance of Galaxy')
        auto_associate = util.string_as_bool(kwd.get('auto_associate', False))
        if trans.app.config.support_url is not None:
            contact = '<a href="%s">support</a>' % trans.app.config.support_url
        else:
            contact = 'support'
        message = 'Verification failed for an unknown reason.  Please contact %s for assistance.' % (contact)
        status = 'error'
        consumer = trans.app.openid_manager.get_consumer(trans)
        info = consumer.complete(kwd, trans.request.url)
        display_identifier = info.getDisplayIdentifier()
        redirect = kwd.get('redirect', '').strip()
        openid_provider = kwd.get('openid_provider', None)
        if info.status == trans.app.openid_manager.FAILURE and display_identifier:
            message = "Login via OpenID failed.  The technical reason for this follows, please include this message in your email if you need to %s to resolve this problem: %s" % (contact, info.message)
            return trans.show_error_message(message)
        elif info.status == trans.app.openid_manager.SUCCESS:
            if info.endpoint.canonicalID:
                display_identifier = info.endpoint.canonicalID
            openid_provider_obj = trans.app.openid_providers.get(openid_provider)
            user_openid = trans.sa_session.query(trans.app.model.UserOpenID).filter(trans.app.model.UserOpenID.table.c.openid == display_identifier).first()
            if not openid_provider_obj and user_openid and user_openid.provider:
                openid_provider_obj = trans.app.openid_providers.get(user_openid.provider)
            if not openid_provider_obj:
                openid_provider_obj = trans.app.openid_providers.new_provider_from_identifier(display_identifier)
            if not user_openid:
                user_openid = trans.app.model.UserOpenID(session=trans.galaxy_session, openid=display_identifier)
            if not user_openid.user:
                user_openid.session = trans.galaxy_session
            if not user_openid.provider and openid_provider:
                user_openid.provider = openid_provider
            if trans.user:
                if user_openid.user and user_openid.user.id != trans.user.id:
                    message = "The OpenID <strong>%s</strong> is already associated with another Galaxy account, <strong>%s</strong>.  Please disassociate it from that account before attempting to associate it with a new account." % (escape(display_identifier), escape(user_openid.user.email))
                if not trans.user.active and trans.app.config.user_activation_on:  # Account activation is ON and the user is INACTIVE.
                    if (trans.app.config.activation_grace_period != 0):  # grace period is ON
                        if self.is_outside_grace_period(trans, trans.user.create_time):  # User is outside the grace period. Login is disabled and he will have the activation email resent.
                            message, status = self.resend_verification_email(trans, trans.user.email, trans.user.username)
                        else:  # User is within the grace period, let him log in.
                            pass
                    else:  # Grace period is off. Login is disabled and user will have the activation email resent.
                        message, status = self.resend_verification_email(trans, trans.user.email, trans.user.username)
                elif not user_openid.user or user_openid.user == trans.user:
                    if openid_provider_obj.id:
                        user_openid.provider = openid_provider_obj.id
                    user_openid.session = trans.galaxy_session
                    if not openid_provider_obj.never_associate_with_user:
                        if not auto_associate and (user_openid.user and user_openid.user.id == trans.user.id):
                            message = "The OpenID <strong>%s</strong> is already associated with your Galaxy account, <strong>%s</strong>." % (escape(display_identifier), escape(trans.user.email))
                            status = "warning"
                        else:
                            message = "The OpenID <strong>%s</strong> has been associated with your Galaxy account, <strong>%s</strong>." % (escape(display_identifier), escape(trans.user.email))
                            status = "done"
                        user_openid.user = trans.user
                        trans.sa_session.add(user_openid)
                        trans.sa_session.flush()
                        trans.log_event("User associated OpenID: %s" % display_identifier)
                    else:
                        message = "The OpenID <strong>%s</strong> cannot be used to log into your Galaxy account, but any post authentication actions have been performed." % escape(openid_provider_obj.name)
                        status = "info"
                    openid_provider_obj.post_authentication(trans, trans.app.openid_manager, info)
                    if redirect:
                        message = '%s<br>Click <a href="%s"><strong>here</strong></a> to return to the page you were previously viewing.' % (message, escape(self.__get_redirect_url(redirect)))
                if redirect and status != "error":
                    return trans.response.send_redirect(self.__get_redirect_url(redirect))
                return trans.response.send_redirect(url_for(controller='openids',
                                                     action='list',
                                                     use_panels=True,
                                                     redirect=redirect,
                                                     message=message,
                                                     status=status))
            elif user_openid.user:
                trans.handle_user_login(user_openid.user)
                trans.log_event("User logged in via OpenID: %s" % display_identifier)
                openid_provider_obj.post_authentication(trans, trans.app.openid_manager, info)
                redirect = self.__get_redirect_url(redirect)
                return trans.response.send_redirect(redirect)
            else:
                trans.sa_session.add(user_openid)
                trans.sa_session.flush()
                message = "OpenID authentication was successful, but you need to associate your OpenID with a Galaxy account. Register a Galaxy account and add your OpenID account in the User Preferences section."
                return trans.show_error_message(message)
        elif info.status == trans.app.openid_manager.CANCEL:
            message = "Login via OpenID was cancelled by an action at the OpenID provider's site."
        elif info.status == trans.app.openid_manager.SETUP_NEEDED:
            if info.setup_url:
                return trans.response.send_redirect(info.setup_url)
            else:
                message = "Unable to log in via OpenID.  Setup at the provider is required before this OpenID can be used.  Please visit your provider's site to complete this step."
        return trans.show_error_message(message)

    @web.expose
    @web.require_login('create OpenIDs')
    def create_openid(self, trans, **kwd):
        return trans.fill_template('/user/openid_manage.mako',
           openid_providers=trans.app.openid_providers,
           redirect=kwd.get('redirect', url_for(controller='openids', action='list')).strip())

    @web.expose_api
    @web.require_login('manage OpenIDs')
    def openids_list(self, trans, **kwd):
        '''List of availabel OpenIDs for user'''
        message = kwd.get('message', '')
        status = kwd.get('status', '')
        if not trans.app.config.enable_openid:
            message = 'OpenID authentication is not enabled in this instance of Galaxy.'
            status = 'error'
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            ids = util.listify(kwd.get('id'))
            if operation == 'delete':
                if not ids:
                    message = 'You must select at least one OpenID to disassociate from your Galaxy account.'
                    status = 'error'
                else:
                    user_openids = []
                    for id in ids:
                        id = trans.security.decode_id(id)
                        user_openid = trans.sa_session.query(trans.app.model.UserOpenID).get(int(id))
                        if not user_openid or (trans.user.id != user_openid.user_id):
                            message = 'The selected OpenID(s) are not associated with your Galaxy account.'
                            status = 'error'
                            user_openids = []
                            break
                        user_openids.append(user_openid)
                    if user_openids:
                        deleted_urls = []
                        for user_openid in user_openids:
                            trans.sa_session.delete(user_openid)
                            deleted_urls.append(user_openid.openid)
                        trans.sa_session.flush()
                        for deleted_url in deleted_urls:
                            trans.log_event('User disassociated OpenID: %s' % deleted_url)
                        message = '%s OpenIDs were disassociated from your Galaxy account.' % len(ids)
                        status = 'done'
        if message and status:
            kwd['message'] = util.sanitize_text(message)
            kwd['status'] = status
        kwd['dict_format'] = True
        return self.user_openid_grid(trans, **kwd)

    @expose_api_anonymous_and_sessionless
    def login(self, trans, payload={}, **kwd):
        '''Handle Galaxy Log in'''
        if "openid_provider" in payload or "openid_url" in payload:
            return self.__openid_auth(trans, payload, **kwd)
        return self.__validate_login(trans, payload, **kwd)

    def __openid_auth(self, trans, payload=None, **kwd):
        '''Handles user request to access an OpenID provider'''
        if not trans.app.config.enable_openid:
            return self.message_exception(trans, 'OpenID authentication is not enabled in this instance of Galaxy.')
        message = 'Unspecified failure authenticating via OpenID.'
        auto_associate = util.string_as_bool(payload.get('auto_associate', False))
        consumer = trans.app.openid_manager.get_consumer(trans)
        openid_url = payload.get('openid_url')
        openid_provider = payload.get('openid_provider')
        redirect = payload.get('redirect')
        method = payload.get('method')
        if openid_url:
            openid_provider_obj = trans.app.openid_providers.new_provider_from_identifier(openid_url)
        elif openid_provider:
            openid_provider_obj = trans.app.openid_providers.get(openid_provider)
        else:
            return self.message_exception(trans, 'An OpenID provider was not specified.')
        if openid_provider_obj:
            process_url = trans.request.base.rstrip('/') + url_for(controller='user', action='openid_process', redirect=redirect, openid_provider=openid_provider, auto_associate=auto_associate)
            request = None
            try:
                request = consumer.begin(openid_provider_obj.op_endpoint_url)
                if request is None:
                    message = 'No OpenID services are available at %s.' % openid_provider_obj.op_endpoint_url
                    return self.message_exception(trans, message)
            except Exception as e:
                return self.message_exception(trans, 'Failed to begin OpenID authentication: %s.' % str(e))
            if request is not None:
                trans.app.openid_manager.add_sreg(trans, request, required=openid_provider_obj.sreg_required, optional=openid_provider_obj.sreg_optional)
                openid_redirect = request.redirectURL(trans.request.base, process_url)
                trans.app.openid_manager.persist_session(trans, consumer)
                if method == "redirect":
                    trans.response.send_redirect(openid_redirect)
                return {"openid_redirect": openid_redirect}
        return {"status": "error", "message": message}

    def __handle_role_and_group_auto_creation(self, trans, user, roles, auto_create_roles=False,
                                              auto_create_groups=False, auto_assign_roles_to_groups_only=False):
        for role_name in roles:
            role = None
            group = None
            if auto_create_roles:
                try:
                    # first try to find the role
                    role = trans.app.security_agent.get_role(role_name)
                except NoResultFound:
                    # or create it
                    role, num_in_groups = trans.app.security_agent.create_role(
                        role_name, "Auto created upon user registration", [], [],
                        create_group_for_role=auto_create_groups)
                    if auto_create_groups:
                        trans.log_event("Created role and group for auto-registered user.")
                    else:
                        trans.log_event("Created role for auto-registered user.")
            if auto_create_groups:
                # only create a group if not existing yet
                try:
                    group = self.sa_session.query(trans.app.model.Group).filter(
                        trans.app.model.Group.table.c.name == role_name).first()
                except NoResultFound:
                    group = self.model.Group(name=role_name)
                    self.sa_session.add(group)
                trans.app.security_agent.associate_user_group(user, group)

            if auto_assign_roles_to_groups_only and group and role:
                trans.log_event("Assigning role to group only")
                trans.app.security_agent.associate_group_role(group, role)
            elif not auto_assign_roles_to_groups_only and role:
                trans.log_event("Assigning role to newly created user")
                trans.app.security_agent.associate_user_role(user, role)

    def __validate_login(self, trans, payload=None, **kwd):
        '''Handle Galaxy Log in'''
        payload = payload or {}
        login = kwd.get("login", payload.get("login"))
        password = kwd.get("password", payload.get("password"))
        status = None
        if not login or not password:
            return self.message_exception(trans, "Please specify a username and password.")
        user = trans.sa_session.query(trans.app.model.User).filter(or_(
            trans.app.model.User.table.c.email == login,
            trans.app.model.User.table.c.username == login
        )).first()
        log.debug("trans.app.config.auth_config_file: %s" % trans.app.config.auth_config_file)
        if user is None:
            message, status, user, success = self.__autoregistration(trans, login, password, status, kwd)
            if not success:
                return self.message_exception(trans, message)
        elif user.deleted:
            message = "This account has been marked deleted, contact your local Galaxy administrator to restore the account."
            if trans.app.config.error_email_to is not None:
                message += " Contact: %s" % trans.app.config.error_email_to
            return self.message_exception(trans, message)
        elif user.external:
            message = "This account was created for use with an external authentication method, contact your local Galaxy administrator to activate it."
            if trans.app.config.error_email_to is not None:
                message += " Contact: %s" % trans.app.config.error_email_to
            return self.message_exception(trans, message)
        elif not trans.app.auth_manager.check_password(user, password):
            return self.message_exception(trans, "Invalid password.")
        elif trans.app.config.user_activation_on and not user.active:  # activation is ON and the user is INACTIVE
            if (trans.app.config.activation_grace_period != 0):  # grace period is ON
                if self.is_outside_grace_period(trans, user.create_time):  # User is outside the grace period. Login is disabled and he will have the activation email resent.
                    message, status = self.resend_verification_email(trans, user.email, user.username, unescaped=True)
                    return self.message_exception(trans, message, sanitize=False)
                else:  # User is within the grace period, let him log in.
                    trans.handle_user_login(user)
                    trans.log_event("User logged in")
            else:  # Grace period is off. Login is disabled and user will have the activation email resent.
                message, status = self.resend_verification_email(trans, user.email, user.username)
                return self.message_exception(trans, message, sanitize=False)
        else:  # activation is OFF
            pw_expires = trans.app.config.password_expiration_period
            if pw_expires and user.last_password_change < datetime.today() - pw_expires:
                # Password is expired, we don't log them in.
                return self.message_exception(trans, "Your password has expired. Please change it to access Galaxy.")
            trans.handle_user_login(user)
            trans.log_event("User logged in")
            if pw_expires and user.last_password_change < datetime.today() - timedelta(days=pw_expires.days / 10):
                # If password is about to expire, modify message to state that.
                expiredate = datetime.today() - user.last_password_change + pw_expires
                return {"message": "Your password will expire in %s days." % expiredate.days, "status": "warning"}
        return {"message": "Success."}

    def __autoregistration(self, trans, login, password, status, kwd, no_password_check=False, cntrller=None):
        """
        Does the autoregistration if enabled. Returns a message
        """
        autoreg = trans.app.auth_manager.check_auto_registration(trans, login, password, no_password_check=no_password_check)
        user = None
        success = False
        if autoreg["auto_reg"]:
            kwd["email"] = autoreg["email"]
            kwd["username"] = autoreg["username"]
            message = " ".join([validate_email(trans, kwd["email"], allow_empty=True),
                                validate_publicname(trans, kwd["username"])]).rstrip()
            if not message:
                message, status, user, success = trans.app.auth_manager.register(trans, **kwd)
                if success:
                    # The handle_user_login() method has a call to the history_set_default_permissions() method
                    # (needed when logging in with a history), user needs to have default permissions set before logging in
                    if not trans.user_is_admin():
                        trans.handle_user_login(user)
                        trans.log_event("User (auto) created a new account")
                        trans.log_event("User logged in")
                    if "attributes" in autoreg and "roles" in autoreg["attributes"]:
                        self.__handle_role_and_group_auto_creation(
                            trans, user, autoreg["attributes"]["roles"],
                            auto_create_groups=autoreg["auto_create_groups"],
                            auto_create_roles=autoreg["auto_create_roles"],
                            auto_assign_roles_to_groups_only=autoreg["auto_assign_roles_to_groups_only"])
                else:
                    message = "Auto-registration failed, contact your local Galaxy administrator. %s" % message
            else:
                message = "Auto-registration failed, contact your local Galaxy administrator. %s" % message
        else:
            message = "No such user or invalid password."
        return message, status, user, success

    @web.expose
    def resend_verification(self, trans):
        """
        Exposed function for use outside of the class. E.g. when user click on the resend link in the masthead.
        """
        message, status = self.resend_verification_email(trans, None, None)
        if status == 'done':
            return trans.show_ok_message(message)
        else:
            return trans.show_error_message(message)

    def resend_verification_email(self, trans, email, username):
        """
        Function resends the verification email in case user wants to log in with an inactive account or he clicks the resend link.
        """
        if email is None:  # User is coming from outside registration form, load email from trans
            email = trans.user.email
        if username is None:  # User is coming from outside registration form, load email from trans
            username = trans.user.username
        is_activation_sent = trans.app.auth_manager.send_verification_email(trans, email, username)
        if is_activation_sent:
            message = 'This account has not been activated yet. The activation link has been sent again. Please check your email address <b>%s</b> including the spam/trash folder.<br><a target="_top" href="%s">Return to the home page</a>.' % (escape(email), url_for('/'))
            status = 'error'
        else:
            message = 'This account has not been activated yet but we are unable to send the activation link. Please contact your local Galaxy administrator.<br><a target="_top" href="%s">Return to the home page</a>.' % url_for('/')
            status = 'error'
            if trans.app.config.error_email_to is not None:
                message += '<br>Error contact: %s' % trans.app.config.error_email_to
        return message, status

    def is_outside_grace_period(self, trans, create_time):
        """
        Function checks whether the user is outside the config-defined grace period for inactive accounts.
        """
        #  Activation is forced and the user is not active yet. Check the grace period.
        activation_grace_period = trans.app.config.activation_grace_period
        delta = timedelta(hours=int(activation_grace_period))
        time_difference = datetime.utcnow() - create_time
        return (time_difference > delta or activation_grace_period == 0)

    @web.expose
    def logout(self, trans, logout_all=False, **kwd):
        if trans.webapp.name == 'galaxy':
            csrf_check = trans.check_csrf_token()
            if csrf_check:
                return csrf_check

            if trans.app.config.require_login:
                refresh_frames = ['masthead', 'history', 'tools']
            else:
                refresh_frames = ['masthead', 'history']
            if trans.user:
                # Queue a quota recalculation (async) task -- this takes a
                # while sometimes, so we don't want to block on logout.
                send_local_control_task(trans.app,
                                        'recalculate_user_disk_usage',
                                        {'user_id': trans.security.encode_id(trans.user.id)})
            # Since logging an event requires a session, we'll log prior to ending the session
            trans.log_event("User logged out")
        else:
            refresh_frames = ['masthead']
        trans.handle_user_logout(logout_all=logout_all)
        message = 'You have been logged out.<br>To log in again <a target="_top" href="%s">go to the home page</a>.' % \
            (url_for('/'))
        if biostar.biostar_logged_in(trans):
            biostar_url = biostar.biostar_logout(trans)
            if biostar_url:
                # TODO: It would be better if we automatically logged this user out of biostar
                message += '<br>To logout of Biostar, please click <a href="%s" target="_blank">here</a>.' % (biostar_url)
        if trans.app.config.use_remote_user and trans.app.config.remote_user_logout_href:
            trans.response.send_redirect(trans.app.config.remote_user_logout_href)
        else:
            return trans.fill_template('/user/logout.mako',
                                       refresh_frames=refresh_frames,
                                       message=message,
                                       status='done',
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
        is_admin = trans.user_is_admin()
        success = False
        show_user_prepopulate_form = False
        if not trans.app.config.allow_user_creation and not trans.user_is_admin():
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
                    message = self.__validate(trans, params, email, password, confirm, username)
                    if not message:
                        # All the values are valid
                        message, status, user, success = trans.app.auth_manager.register(trans, subscribe_checked=subscribe_checked, **kwd)
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
        return trans.fill_template('/user/register.mako',
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

    @web.expose
    def activate(self, trans, **kwd):
        """
        Check whether token fits the user and then activate the user's account.
        """
        params = util.Params(kwd, sanitize=False)
        email = params.get('email', None)
        if email is not None:
            email = unquote(email)
        activation_token = params.get('activation_token', None)

        if email is None or activation_token is None:
            #  We don't have the email or activation_token, show error.
            return trans.show_error_message("You are using an invalid activation link. Try to log in and we will send you a new activation email. <br><a href='%s'>Go to login page.</a>") % web.url_for(controller="root", action="index")
        else:
            # Find the user
            user = trans.sa_session.query(trans.app.model.User).filter(trans.app.model.User.table.c.email == email).first()
            if not user:
                # Probably wrong email address
                return trans.show_error_message("You are using an invalid activation link. Try to log in and we will send you a new activation email. <br><a href='%s'>Go to login page.</a>") % web.url_for(controller="root", action="index")
            # If the user is active already don't try to activate
            if user.active is True:
                return trans.show_ok_message("Your account is already active. Nothing has changed. <br><a href='%s'>Go to login page.</a>") % web.url_for(controller='root', action='index')
            if user.activation_token == activation_token:
                user.activation_token = None
                user.active = True
                trans.sa_session.add(user)
                trans.sa_session.flush()
                return trans.show_ok_message("Your account has been successfully activated! <br><a href='%s'>Go to login page.</a>") % web.url_for(controller='root', action='index')
            else:
                #  Tokens don't match. Activation is denied.
                return trans.show_error_message("You are using an invalid activation link. Try to log in and we will send you a new activation email. <br><a href='%s'>Go to login page.</a>") % web.url_for(controller='root', action='index')
        return

    def __validate(self, trans, params, email, password, confirm, username):
        message = "\n".join([validate_email(trans, email),
                             validate_password(trans, password, confirm),
                             validate_publicname(trans, username)]).rstrip()
        return message

    def __get_redirect_url(self, redirect):
        root_url = url_for('/', qualified=True)
        # compare urls, to prevent a redirect from pointing (directly) outside of galaxy
        # or to enter a logout/login loop
        if not redirect or redirect == "None":
            redirect = root_url
        if not util.compare_urls(root_url, redirect, compare_path=False) or util.compare_urls(url_for(controller='user', action='logout', qualified=True), redirect):
            log.warning('Redirect URL is outside of Galaxy, will redirect to Galaxy root instead: %s', redirect)
            redirect = root_url
        elif util.compare_urls(url_for(controller='user', action='logout', qualified=True), redirect):
            redirect = root_url
        return redirect

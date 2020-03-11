"""
SAML 2 Authentication Controller.
"""

from __future__ import absolute_import

import logging

from sqlalchemy.orm.exc import NoResultFound

from datetime import datetime, timedelta
from galaxy import web
from galaxy.exceptions import Conflict
from galaxy.web import url_for
from galaxy.webapps.base.controller import JSAppLauncher
from galaxy import (
    exceptions,
    model,
    util
)
from galaxy.managers import (
    api_keys,
    base,
    deletable
)
from galaxy.security.validate_user_input import (
    validate_email,
    validate_password,
    validate_publicname
)
from galaxy.util.hash_util import new_secure_hash
from galaxy.web import url_for

log = logging.getLogger(__name__)

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import json

class SAML(JSAppLauncher):

    def prepare_request(self, request):
        return {
            'https': 'on' if request.scheme == 'https' else 'off',
            'http_host': request.host,
            'server_port': request.server_port,
            'script_name': request.script_name,
            'get_data': request.urlargs,
            'post_data': request.POST
        }

    def init_saml_auth(self, trans):
        req = self.prepare_request(trans.request)
        return OneLogin_Saml2_Auth(req, custom_base_path=trans.app.config.saml_config_dir)

    @web.json
    @web.expose
    def login(self, trans, provider):
        log.debug("Handling SAML authentication")
        if not trans.app.config.enable_saml:
            msg = "Login to Galaxy using SAML identities is not enabled on this Galaxy instance."
            log.debug(msg)
            return trans.show_error_message(msg)
        log.debug("Loading config from " + trans.app.config.saml_config_dir)
        auth = self.init_saml_auth(trans)
        log.debug("Create auth object")
        return_to = trans.request.host_url
        redirect = auth.login(return_to)
        log.debug("return_to: " + return_to)
        log.debug("redirect to: " + redirect)
        # return trans.response.send_redirect(redirect)
        return {"redirect_uri": redirect}

    def _old_login(self, trans, provider):
        log.debug("Handling SAML authentication")
        if not trans.app.config.enable_saml:
            msg = "Login to Galaxy using SAML identities is not enabled on this Galaxy instance."
            log.debug(msg)
            return trans.show_error_message(msg)
        # success, message, redirect_uri = trans.app.authnz_manager.authenticate(provider, trans)
        success = True
        login = "galaxy@lappsgrid.org"
        user = trans.sa_session.query(trans.app.model.User).filter(
            trans.app.model.User.table.c.email == login
        ).first()

        # user = trans.app.user_manager.create(email=email, username=username)
        # user.set_random_password()
        # trans.sa_session.add(user)
        # trans.sa_session.flush()
        if user is None:
            log.debug("Attempting to create user.")
            try:
                user = trans.app.user_manager.create(email=login, username="galaxy")
                # message, user = self.__autoregistration(trans, login, "")
                # if message:
                #     return self.message_exception(trans, message)
            except:
                return self.message_exception(trans, "Unable to create user.")
            user.active = True
            log.debug("User created. Setting password")
            user.set_random_password()
            log.debug("Password set. Adding user")
            trans.sa_session.add(user)
            log.debug("User added. Flushing session")
            trans.sa_session.flush()
            log.debug("Session flushed")

        if success:
            log.debug("handling user login.")
            trans.handle_user_login(user)
            return {"redirect_uri": url_for("/")}
        else:
            raise exceptions.AuthenticationFailed("Authentication failed.")


    @web.expose
    def assertion_consumer_service(self, trans):
        # req = prepare_request(request)
        auth = self.init_saml_auth(trans)

        session = trans.galaxy_session
        request_id = None
        if 'AuthNRequestID' in session:
            request_id = session['AuthNRequestID']

        auth.process_response(request_id=request_id)
        errors = auth.get_errors()
        not_auth_warn = not auth.is_authenticated()
        if len(errors) == 0:
            if 'AuthNRequestID' in session:
                del session['AuthNRequestID']
            session['samlUserdata'] = auth.get_attributes()
            session['samlNameId'] = auth.get_nameid()
            session['samlNameIdFormat'] = auth.get_nameid_format()
            session['samlNameIdNameQualifier'] = auth.get_nameid_nq()
            session['samlNameIdSPNameQualifier'] = auth.get_nameid_spnq()
            session['samlSessionIndex'] = auth.get_session_index()
            self_url = OneLogin_Saml2_Utils.get_self_url(req)
            form = trans.request.POST
            if 'RelayState' in form and self_url != form['RelayState']:
                redirect_to = auth.redirect_to(form['RelayState'])
                return {"redirect_uri": redirect_to}
        elif auth.get_settings().is_debug_active():
            error_reason = auth.get_last_error_reason()
        return { "redirect_url": url_for("/") }

    @web.expose
    def logout(self, trans, *args, **kwargs):
        log.debug("Logout called")
        return { 'redirect_url': url_for('/')}

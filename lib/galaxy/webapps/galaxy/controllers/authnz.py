"""
OAuth 2.0 and OpenID Connect Authentication and Authorization Controller.
"""

from __future__ import absolute_import
import logging
from galaxy import web
from galaxy.web import url_for
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger(__name__)


class OIDC(BaseUIController):

    @web.expose
    def login(self, trans, provider):
        success, message, redirect_uri = trans.app.authnz_manager.authenticate(provider, trans)
        return trans.response.send_redirect(web.url_for(redirect_uri))

    @web.expose
    def callback(self, trans, provider, **kwargs):
        if 'error' in kwargs:
            # TODO: handle error
            print 'kwargs: ', kwargs
            raise
        success, message, (redirect_url, user) = trans.app.authnz_manager.callback(provider, kwargs['state'], kwargs['code'], trans, login_redirect_url=url_for('/'))
        trans.handle_user_login(user)
        return trans.fill_template('/user/login.mako',
                                   login=user.username,
                                   header="",
                                   use_panels=False,
                                   redirect_url="http://localhost:8080/",
                                   redirect='http://localhost:8080/',
                                   refresh_frames='refresh_frames',
                                   message="You are now logged in as user0@eee.com",
                                   status='done',
                                   openid_providers=trans.app.openid_providers,
                                   form_input_auto_focus=True,
                                   active_view="user")

    @web.expose
    @web.require_login("authenticate against Google identity provider")
    def disconnect(self, trans, provider, **kwargs):
        if trans.user is None:
            # Only logged in users are allowed here.
            return
        success, message, redirect_url = trans.app.authnz_manager.disconnect(provider,
                                                                             trans,
                                                                             disconnect_redirect_url=url_for('/'))
        return trans.response.send_redirect(redirect_url)

# TODO: check for the error: AuthAlreadyAssociated: This google-openidconnect account is already in use.
# it happens when authenticating a user whose previous authentication was disconnected.

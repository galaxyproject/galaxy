"""
OAuth 2.0 and OpenID Connect Authentication and Authorization Controller.
"""

from __future__ import absolute_import
import logging
log = logging.getLogger(__name__)
from galaxy import web
from galaxy.web.base.controller import BaseUIController


class OIDC(BaseUIController):

    @web.expose
    def login(self, trans, **kwargs):
        return trans.response.send_redirect(web.url_for(trans.app.authnz_manager.authenticate("Google", trans)))

    @web.expose
    def callback(self, trans, **kwargs):
        if 'error' in kwargs:
            # TODO: handle error
            print 'kwargs: ', kwargs
            raise
        #TODO: make the following more generic, the attributes state and code are Google specific.
        redirect_url, user = trans.app.authnz_manager.callback("Google", kwargs['state'], kwargs['code'], trans)
        trans.handle_user_login(user)
        return trans.response.send_redirect(redirect_url)

    @web.expose
    @web.require_login("authenticate against Google identity provider")
    def disconnect(self, trans, **kwargs):
        if trans.user is None:
            # Only logged in users are allowed here.
            return
        return trans.response.send_redirect(trans.app.authnz_manager.disconnect('Google', trans, redirect_url=None))

# TODO: check for the error: AuthAlreadyAssociated: This google-openidconnect account is already in use.
# it happens when authenticating a user whose previous authentication was disconnected.

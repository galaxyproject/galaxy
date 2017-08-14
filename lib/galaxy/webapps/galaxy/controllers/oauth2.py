"""
OAuth 2.0 and OpenID Connect Authentication and Authorization Controller.
"""

from __future__ import absolute_import
import logging
log = logging.getLogger(__name__)
from galaxy import web
from galaxy.web.base.controller import BaseUIController

class OAuth2( BaseUIController ):

    @web.expose
    @web.require_login( "authenticate against Google identity provider" )
    def google_authn(self, trans, **kwargs):
        if trans.user is None:
            # Only logged in users are allowed here.
            return
        return trans.response.send_redirect( web.url_for( trans.app.authnz_manager.authenticate( "Google", trans ) ) )

    @web.expose
    def google_callback(self, trans, **kwargs):  # TODO: to be tested.
        if trans.app.authnz_manager.callback( "Google", kwargs[ 'state' ], kwargs[ 'code' ], trans ) is False:
            # TODO: inform user why he/she is being re-authenticated.
            self.google_authn( trans )
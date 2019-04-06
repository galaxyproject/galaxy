"""
Contains the OpenID interface in the Universe class
"""

import logging

from markupsafe import escape

import galaxy.util
from galaxy import web
from galaxy.web import error, url_for
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger(__name__)


class OpenID(BaseUIController):

    @web.expose
    def openid_auth(self, trans, **kwd):
        '''Handles user request to access an OpenID provider'''
        if not trans.app.config.enable_openid:
            return trans.show_error_message("OpenID authentication is not enabled in this instance of Galaxy.")
        consumer = trans.app.openid_manager.get_consumer(trans)
        openid_provider = kwd.get('openid_provider')
        if openid_provider:
            openid_provider_obj = trans.app.openid_providers.get(openid_provider)
        else:
            return trans.show_error_message("An OpenID provider was not specified.")
        if not openid_provider_obj:
            return trans.show_error_message("An OpenID provider is invalid.")
        process_url = trans.request.base.rstrip('/') + url_for(controller='openid', action='openid_process', openid_provider=openid_provider)
        request = None
        try:
            request = consumer.begin(openid_provider_obj.op_endpoint_url)
            if request is None:
                return trans.show_error_message("No OpenID services are available at %s." % openid_provider_obj.op_endpoint_url)
        except Exception as e:
            return trans.show_error_message("Failed to begin OpenID authentication: %s." % str(e))
        if request is not None:
            trans.app.openid_manager.add_sreg(trans, request, required=openid_provider_obj.sreg_required, optional=openid_provider_obj.sreg_optional)
            if request.shouldSendRedirect():
                redirect_url = request.redirectURL(
                    trans.request.base, process_url)
                trans.app.openid_manager.persist_session(trans, consumer)
                return trans.response.send_redirect(redirect_url)
            else:
                form = request.htmlMarkup(trans.request.base, process_url, form_tag_attrs={'id': 'openid_message', 'target': '_top'})
                trans.app.openid_manager.persist_session(trans, consumer)
                return form
        return trans.show_error_message("OpenID request failed.")

    @web.expose
    def openid_process(self, trans, **kwd):
        '''Handle's response from OpenID Providers'''
        return_link = "Click <a href='%s'>here</a> to return." % url_for("/")
        if not trans.app.config.enable_openid:
            return trans.show_error_message("OpenID authentication is not enabled in this instance of Galaxy. %s" % return_link)
        consumer = trans.app.openid_manager.get_consumer(trans)
        info = consumer.complete(kwd, trans.request.url)
        display_identifier = info.getDisplayIdentifier()
        openid_provider = kwd.get('openid_provider', None)
        if info.status == trans.app.openid_manager.SUCCESS:
            if info.endpoint.canonicalID:
                display_identifier = info.endpoint.canonicalID
            openid_provider_obj = trans.app.openid_providers.get(openid_provider)
            openid_provider_obj.post_authentication(trans, trans.app.openid_manager, info)
            return trans.show_message("Processed OpenID authentication. %s" % return_link)
        else:
            return trans.show_error_message("Authentication via OpenID failed: %s. %s" % (info.message, return_link))

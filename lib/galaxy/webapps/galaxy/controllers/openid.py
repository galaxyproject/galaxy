"""
Contains the OpenID interface in the Universe class
"""

import logging

from galaxy import web
from galaxy.openid.openid_manager import OpenIDManager
from galaxy.openid.providers import OpenIDProviders
from galaxy.util import unicodify
from galaxy.web import url_for
from galaxy.webapps.base.controller import BaseUIController

log = logging.getLogger(__name__)


class OpenID(BaseUIController):

    def __init__(self, app):
        super().__init__(app)
        if app.config.enable_openid:
            self.openid_manager = OpenIDManager(app.config.openid_consumer_cache_path)
            self.openid_providers = OpenIDProviders.from_file('lib/galaxy/openid/openid_conf.xml')

    @web.expose
    def openid_auth(self, trans, **kwd):
        '''Handles user request to access an OpenID provider'''
        if not trans.app.config.enable_openid:
            return trans.show_error_message("OpenID authentication is not enabled in this instance of Galaxy.")
        consumer = self.openid_manager.get_consumer(trans)
        openid_provider = kwd.get('openid_provider')
        if openid_provider:
            openid_provider_obj = self.openid_providers.get(openid_provider)
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
            return trans.show_error_message("Failed to begin OpenID authentication: %s." % unicodify(e))
        if request is not None:
            self.openid_manager.add_sreg(trans, request, required=openid_provider_obj.sreg_required, optional=openid_provider_obj.sreg_optional)
            if request.shouldSendRedirect():
                redirect_url = request.redirectURL(
                    trans.request.base, process_url)
                self.openid_manager.persist_session(trans, consumer)
                return trans.response.send_redirect(redirect_url)
            else:
                form = request.htmlMarkup(trans.request.base, process_url, form_tag_attrs={'id': 'openid_message', 'target': '_top'})
                self.openid_manager.persist_session(trans, consumer)
                return form
        return trans.show_error_message("OpenID request failed.")

    @web.expose
    def openid_process(self, trans, **kwd):
        '''Handle's response from OpenID Providers'''
        return_link = "Click <a href='%s'>here</a> to return." % url_for("/")
        if not trans.app.config.enable_openid:
            return trans.show_error_message("OpenID authentication is not enabled in this instance of Galaxy. %s" % return_link)
        consumer = self.openid_manager.get_consumer(trans)
        info = consumer.complete(kwd, trans.request.url)
        openid_provider = kwd.get('openid_provider', None)
        if info.status == self.openid_manager.SUCCESS:
            openid_provider_obj = self.openid_providers.get(openid_provider)
            openid_provider_obj.post_authentication(trans, self.openid_manager, info)
            return trans.show_message("Processed OpenID authentication. %s" % return_link)
        else:
            return trans.show_error_message("Authentication via OpenID failed: {}. {}".format(info.message, return_link))

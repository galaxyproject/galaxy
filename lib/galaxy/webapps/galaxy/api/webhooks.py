"""
API Controller providing Galaxy Webhooks
"""

from galaxy.web import _future_expose_api_anonymous_and_sessionless as \
    expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController

import logging
import random
import imp

log = logging.getLogger(__name__)


class WebhooksController(BaseAPIController):
    def __init__(self, app):
        super(WebhooksController, self).__init__(app)

    @expose_api_anonymous_and_sessionless
    def get_all(self, trans, **kwd):
        """
        *GET /api/webhooks/
        Returns all webhooks
        """
        return [w.to_dict() for w in self.app.webhooks_registry.webhooks]

    @expose_api_anonymous_and_sessionless
    def get_random(self, trans, webhook_type, **kwd):
        """
        *GET /api/webhooks/{webhook_type}
        Returns a random webhook for a given type
        """
        webhooks = [w for w in self.app.webhooks_registry.webhooks
                    if w.type == webhook_type]
        return random.choice(webhooks).to_dict() if webhooks else {}

    @expose_api_anonymous_and_sessionless
    def get_data(self, trans, webhook_name, **kwd):
        """
        *GET /api/webhooks/{webhook_name}/get_data
        Returns the result of executing helper function
        """
        webhook = [w for w in self.app.webhooks_registry.webhooks
                   if w.name == webhook_name]
        return imp.load_source('helper', webhook[0].helper).main(webhook[0]) \
            if webhook and webhook[0].helper != '' else {}

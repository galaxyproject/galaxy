"""
API Controller providing Galaxy Webhooks
"""

from galaxy.web import _future_expose_api_anonymous_and_sessionless as \
    expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController

import logging
import random

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
        return self.app.webhooks_registry.webhooks

    @expose_api_anonymous_and_sessionless
    def get_random(self, trans, webhook_type, **kwd):
        """
        *GET /api/webhooks/{webhook_type}
        Returns a random webhook for a given type
        """
        webhooks = self.app.webhooks_registry.webhooks[webhook_type]
        return random.choice(webhooks)

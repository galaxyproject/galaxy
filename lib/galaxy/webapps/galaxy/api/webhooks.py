"""
API Controller providing Galaxy Webhooks
"""
import imp
import logging

from galaxy.web import _future_expose_api_anonymous_and_sessionless as \
    expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class WebhooksController(BaseAPIController):
    def __init__(self, app):
        super(WebhooksController, self).__init__(app)

    @expose_api_anonymous_and_sessionless
    def all_webhooks(self, trans, **kwd):
        """
        *GET /api/webhooks/
        Returns all webhooks
        """
        return [
            webhook.to_dict()
            for webhook in self.app.webhooks_registry.webhooks
        ]

    @expose_api_anonymous_and_sessionless
    def webhook_data(self, trans, webhook_id, **kwd):
        """
        *GET /api/webhooks/{webhook_id}/data/{params}
        Returns the result of executing helper function
        """
        params = {}

        for key, value in kwd.items():
            params[key] = value

        webhook = next(
            webhook
            for webhook in self.app.webhooks_registry.webhooks
            if webhook.id == webhook_id
        )

        return imp.load_source(webhook.path, webhook.helper).main(
            trans, webhook, params,
        ) if webhook and webhook.helper != '' else {}

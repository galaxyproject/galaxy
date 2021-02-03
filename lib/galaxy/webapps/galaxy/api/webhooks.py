"""
API Controller providing Galaxy Webhooks
"""
import imp
import logging
from typing import Any

from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.base.controller import BaseAPIController
from galaxy.webapps.base.webapp import GalaxyWebTransaction

log = logging.getLogger(__name__)


class WebhooksController(BaseAPIController):

    @expose_api_anonymous_and_sessionless
    def all_webhooks(self, trans: GalaxyWebTransaction, **kwd):
        """
        GET /api/webhooks/

        Return all webhooks.
        """
        return [
            webhook.to_dict()
            for webhook in self.app.webhooks_registry.webhooks
        ]

    @expose_api_anonymous_and_sessionless
    def webhook_data(self, trans: Any, webhook_id, **kwd):
        """
        GET /api/webhooks/{webhook_id}/data/{params}

        Return the result of executing helper function.
        """
        params = {}

        for key, value in kwd.items():
            params[key] = value

        webhook = next(
            webhook
            for webhook in self.app.webhooks_registry.webhooks
            if webhook.id == webhook_id
        )

        if webhook and webhook.helper != '':
            return imp.load_source(webhook.path, webhook.helper).main(  # type: ignore
                trans, webhook, params,
            )
        else:
            return {}

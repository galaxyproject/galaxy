"""
API Controller providing Galaxy Webhooks
"""
import importlib.util
import logging
from typing import Any

from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class WebhooksController(BaseGalaxyAPIController):
    @expose_api_anonymous_and_sessionless
    def all_webhooks(self, trans: GalaxyWebTransaction, **kwd):
        """
        GET /api/webhooks/

        Return all webhooks.
        """
        return [webhook.to_dict() for webhook in self.app.webhooks_registry.webhooks]

    @expose_api_anonymous_and_sessionless
    def webhook_data(self, trans: Any, webhook_id, **kwd):
        """
        GET /api/webhooks/{webhook_id}/data/{params}

        Return the result of executing helper function.
        """
        params = {}

        for key, value in kwd.items():
            params[key] = value

        webhook = next(webhook for webhook in self.app.webhooks_registry.webhooks if webhook.id == webhook_id)

        if webhook and webhook.helper != "":
            spec = importlib.util.spec_from_file_location(webhook.path, webhook.helper)
            assert spec
            module = importlib.util.module_from_spec(spec)
            assert spec.loader
            spec.loader.exec_module(module)
            return module.main(
                trans,
                webhook,
                params,
            )
        else:
            return {}

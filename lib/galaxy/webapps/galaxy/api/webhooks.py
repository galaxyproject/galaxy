"""
API Controller providing Galaxy Webhooks
"""

import logging

from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class WebhooksController(BaseAPIController):
    def __init__(self, app):
        super(WebhooksController, self).__init__(app)

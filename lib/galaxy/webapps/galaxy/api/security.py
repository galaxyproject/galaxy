import logging

from galaxy.web import (
    expose_api,
    require_admin
)
from galaxy.webapps.base.controller import (
    BaseAPIController,
    UsesVisualizationMixin
)

log = logging.getLogger(__name__)


class SecurityController(BaseAPIController):

    @require_admin
    @expose_api
    def decode_id(self, trans, **kwd):
        encoded_id = kwd["id"]
        return trans.security.decode_id(encoded_id)

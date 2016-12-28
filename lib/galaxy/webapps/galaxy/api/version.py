"""
API to show galaxy version information
"""
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController

from galaxy.version import VERSION

import logging
log = logging.getLogger(__name__)


class RemoteFilesAPIController(BaseAPIController):

    @expose_api
    def index(self, trans):
        """
        GET /api/version/

        Displays version/system information

        :returns:   dictionary of information
        :rtype:     dict
        """
        response = {
            'version': VERSION
        }
        return response

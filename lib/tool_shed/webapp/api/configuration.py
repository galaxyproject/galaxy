"""
API operations allowing clients to determine Tool Shed instance's
capabilities and configuration settings.
"""

import logging

from galaxy.web import expose_api_anonymous_and_sessionless
from . import BaseShedAPIController

log = logging.getLogger(__name__)


class ConfigurationController(BaseShedAPIController):
    @expose_api_anonymous_and_sessionless
    def version(self, trans, **kwds):
        """
        GET /api/version
        Return a description of the version_major and version of Galaxy Tool Shed
        (e.g. 15.07 and 15.07.dev).

        :rtype:     dict
        :returns:   dictionary with versions keyed as 'version_major' and 'version'
        """
        return {"version_major": self.app.config.version_major, "version": self.app.config.version}

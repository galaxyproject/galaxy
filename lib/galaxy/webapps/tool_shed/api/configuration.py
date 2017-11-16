"""
API operations allowing clients to determine Tool Shed instance's
capabilities and configuration settings.
"""
import logging

from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class ConfigurationController(BaseAPIController):

    def __init__(self, app):
        super(ConfigurationController, self).__init__(app)

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

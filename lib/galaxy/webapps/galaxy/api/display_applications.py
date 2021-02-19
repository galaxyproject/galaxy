"""
API operations on annotations.
"""
import logging

from galaxy.app import StructuredApp
from galaxy.managers.display_applications import DisplayApplicationsManager
from galaxy.web import (
    expose_api,
    require_admin,
)
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class DisplayApplicationsController(BaseAPIController):

    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self.manager = DisplayApplicationsManager(app)

    @expose_api
    def index(self, trans, **kwd):
        """
        GET /api/display_applications/

        Returns the list of display applications.

        :returns:   list of available display applications
        :rtype:     list
        """
        return self.manager.index()

    @expose_api
    @require_admin
    def reload(self, trans, payload=None, **kwd):
        """
        POST /api/display_applications/reload

        Reloads the list of display applications.

        :param  ids:  list containing ids of display to be reloaded
        :type   ids:  list
        """
        payload = payload or {}
        ids = payload.get('ids', [])
        return self.manager.reload(ids)

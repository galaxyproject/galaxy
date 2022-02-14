"""
API operations on annotations.
"""
import logging

from galaxy.managers.display_applications import DisplayApplicationsManager
from galaxy.web import (
    expose_api,
    require_admin,
)
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class DisplayApplicationsController(BaseGalaxyAPIController):
    manager = depends(DisplayApplicationsManager)

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
        ids = payload.get("ids", [])
        return self.manager.reload(ids)

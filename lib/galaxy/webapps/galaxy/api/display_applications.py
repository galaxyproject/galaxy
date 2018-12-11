"""
API operations on annotations.
"""
import logging

from galaxy import exceptions
from galaxy.web import expose_api
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class DisplayApplicationsController(BaseAPIController):

    @expose_api
    def index(self, trans, **kwd):
        """
        GET /api/display_applications/

        Returns the list of display applications.

        :returns:   list of available display applications
        :rtype:     list
        """
        response = []
        for display_app in trans.app.datatypes_registry.display_applications.values():

            response.append({
                "id" : display_app.id,
                "name": display_app.name,
                "version": display_app.version,
                "filename_": display_app._filename,
                "links": [{"name": l.name} for l in display_app.links.values()]
            })
        return response


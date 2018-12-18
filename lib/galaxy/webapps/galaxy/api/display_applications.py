"""
API operations on annotations.
"""
import logging

from galaxy import queue_worker
from galaxy.web import expose_api, require_admin
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
                'id' : display_app.id,
                'name': display_app.name,
                'version': display_app.version,
                'filename_': display_app._filename,
                'links': [{'name': l.name} for l in display_app.links.values()]
            })
        return response

    @expose_api
    @require_admin
    def reload(self, trans, payload={}, **kwd):
        """
        POST /api/display_applications/reload

        Reloads the list of display applications.

        :param  ids:  list containing ids of display to be reloaded
        :type   ids:  list
        """
        ids = payload.get('ids')
        queue_worker.send_control_task(trans.app,
            'reload_display_application',
            noop_self=True,
            kwargs={'display_application_ids': ids})
        reloaded, failed = trans.app.datatypes_registry.reload_display_applications(ids)
        if not reloaded and failed:
            message = 'Unable to reload any of the %i requested display applications ("%s").' % (len(failed), '", "'.join(failed))
        elif failed:
            message = 'Reloaded %i display applications ("%s"), but failed to reload %i display applications ("%s").' % (len(reloaded), '", "'.join(reloaded), len(failed), '", "'.join(failed))
        elif not reloaded:
            message = 'You need to request at least one display application to reload.'
        else:
            message = 'Reloaded %i requested display applications ("%s").' % (len(reloaded), '", "'.join(reloaded))
        return {'message': message, 'reloaded': reloaded, 'failed': failed}

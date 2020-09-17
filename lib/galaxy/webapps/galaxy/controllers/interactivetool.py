"""
Provides web interaction with InteractiveTools
"""
import logging

from galaxy import (
    web
)
from galaxy.webapps.base.controller import (
    BaseUIController,
)

log = logging.getLogger(__name__)


class InteractiveTool(BaseUIController):
    @web.expose_api_anonymous
    def list(self, trans, **kwargs):
        """List all available interactivetools"""
        if not trans.app.config.interactivetools_enable:
            raise web.httpexceptions.HTTPNotFound()
        operation = kwargs.get('operation', None)
        message = None
        status = None
        if operation:
            eps = []
            ids = kwargs.get('id', None)
            if ids:
                if not isinstance(ids, list):
                    ids = [ids]
                for entry_point_id in ids:
                    entry_point_id = self.decode_id(entry_point_id)
                    entry_point = trans.sa_session.query(trans.app.model.InteractiveToolEntryPoint).get(entry_point_id)
                    if trans.app.interactivetool_manager.can_access_entry_point(trans, entry_point):
                        eps.append(entry_point)
            if eps:
                failed = []
                succeeded = []
                jobs = []
                if operation == 'stop':
                    for ep in eps:
                        if ep.job not in jobs:
                            stopped = trans.app.interactivetool_manager.stop(trans, ep)
                            if stopped:
                                succeeded.append(ep)
                                jobs.append(ep.job)
                            else:
                                failed.append(ep)
                        else:
                            succeeded.append(ep)
                    if failed:
                        message = 'Unable to stop %i InteractiveTools.' % (len(failed))
                        status = 'error'
                    if succeeded:
                        message = 'Stopped %i InteractiveTools.' % (len(succeeded))
                        status = 'ok'
        if message and status:
            kwargs['message'] = message
            kwargs['status'] = status
        return kwargs

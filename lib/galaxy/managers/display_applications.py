import logging
from typing import (
    Any,
    Dict,
    List,
)

from galaxy.datatypes.registry import Registry
from galaxy.structured_app import StructuredApp

log = logging.getLogger(__name__)


class DisplayApplicationsManager:
    """Interface/service object for sharing logic between controllers."""

    def __init__(self, app: StructuredApp):
        self._app = app

    @property
    def datatypes_registry(self) -> Registry:
        return self._app.datatypes_registry

    def index(self) -> List[Any]:
        """
        Returns the list of display applications.

        :returns:   list of available display applications
        :rtype:     list
        """
        rval = []
        for display_app in self.datatypes_registry.display_applications.values():
            rval.append(
                {
                    "id": display_app.id,
                    "name": display_app.name,
                    "version": display_app.version,
                    "filename_": display_app._filename,
                    "links": [{"name": link.name} for link in display_app.links.values()],
                }
            )
        return rval

    def reload(self, ids: List[str]) -> Dict[str, Any]:
        """
        Reloads the list of display applications.

        :param  ids:  list containing ids of display to be reloaded
        :type   ids:  list
        """
        self._app.queue_worker.send_control_task(
            "reload_display_application", noop_self=True, kwargs={"display_application_ids": ids}
        )
        reloaded, failed = self.datatypes_registry.reload_display_applications(ids)
        if not reloaded and failed:
            message = 'Unable to reload any of the %i requested display applications ("%s").' % (
                len(failed),
                '", "'.join(failed),
            )
        elif failed:
            message = (
                'Reloaded %i display applications ("%s"), but failed to reload %i display applications ("%s").'
                % (len(reloaded), '", "'.join(reloaded), len(failed), '", "'.join(failed))
            )
        elif not reloaded:
            message = "You need to request at least one display application to reload."
        else:
            message = 'Reloaded %i requested display applications ("%s").' % (len(reloaded), '", "'.join(reloaded))
        return {"message": message, "reloaded": reloaded, "failed": failed}

import logging
from typing import (
    List,
    Optional,
)

from pydantic import BaseModel

from galaxy.datatypes.registry import Registry
from galaxy.structured_app import StructuredApp

log = logging.getLogger(__name__)


class Link(BaseModel):
    name: str


class DisplayApplication(BaseModel):
    id: str
    name: str
    version: str
    filename_: str
    links: List[Link]


class ReloadFeedback(BaseModel):
    message: str
    reloaded: List[Optional[str]]
    failed: List[Optional[str]]


class DisplayApplicationsManager:
    """Interface/service object for sharing logic between controllers."""

    def __init__(self, app: StructuredApp):
        self._app = app

    @property
    def datatypes_registry(self) -> Registry:
        return self._app.datatypes_registry

    def index(self) -> List[DisplayApplication]:
        """
        Returns the list of display applications.

        :returns:   list of available display applications
        :rtype:     list
        """
        rval = []
        for display_app in self.datatypes_registry.display_applications.values():
            rval.append(
                DisplayApplication(
                    id=display_app.id,
                    name=display_app.name,
                    version=display_app.version,
                    filename_=display_app._filename,
                    links=[Link(name=link.name) for link in display_app.links.values()],
                )
            )
        return rval

    def reload(self, ids: List[str]) -> ReloadFeedback:
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
            message = 'Unable to reload any of the {} requested display applications ("{}").'.format(
                len(failed),
                '", "'.join(failed),
            )
        elif failed:
            message = (
                'Reloaded {} display applications ("{}"), but failed to reload {} display applications ("{}").'.format(
                    len(reloaded), '", "'.join(reloaded), len(failed), '", "'.join(failed)
                )
            )
        elif not reloaded:
            message = "You need to request at least one display application to reload."
        else:
            message = 'Reloaded {} requested display applications ("{}").'.format(len(reloaded), '", "'.join(reloaded))
        return ReloadFeedback(message=message, reloaded=reloaded, failed=failed)

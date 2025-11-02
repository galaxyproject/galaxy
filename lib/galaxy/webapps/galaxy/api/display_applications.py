"""
API operations on annotations.
"""

import logging
from typing import (
    Any,
    Optional,
)

from fastapi import Body

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.display_applications import (
    CreateLinkFeedback,
    CreateLinkIncoming,
    DisplayApplication,
    DisplayApplicationsManager,
    ReloadFeedback,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["display_applications"])


@router.cbv
class FastAPIDisplayApplications:
    manager: DisplayApplicationsManager = depends(DisplayApplicationsManager)

    @router.get(
        "/api/display_applications",
        public=True,
        summary="Returns the list of display applications.",
        name="display_applications_index",
    )
    def index(
        self,
    ) -> list[DisplayApplication]:
        """
        Returns the list of display applications.
        """
        return self.manager.index()

    @router.post(
        "/api/display_applications/create_link",
        summary="Creates a link for display applications.",
        name="display_applications_create_link",
    )
    def create_link(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateLinkIncoming = Body(...),
    ) -> CreateLinkFeedback:
        """
        Creates a link for display applications.

        :param  app_name:  display application name
        :type   app_name:  string
        :param  dataset_id:  encoded dataset_id
        :type   dataset_id:  string
        :param  link_name:  link name
        :type   link_name:  string
        """
        app_name = payload.app_name
        dataset_id = payload.dataset_id
        link_name = payload.link_name
        kwd = payload.kwd or {}
        result = self.manager.create_link(
            trans,
            app_name=app_name,
            dataset_id=dataset_id,
            link_name=link_name,
            **kwd,
        )
        return result

    @router.post(
        "/api/display_applications/reload",
        summary="Reloads the list of display applications.",
        name="display_applications_reload",
        require_admin=True,
    )
    def reload(
        self,
        payload: Optional[dict[str, list[str]]] = Body(default=None),
    ) -> ReloadFeedback:
        """
        Reloads the list of display applications.
        """
        payload = payload or {}
        ids = payload.get("ids", [])
        result = self.manager.reload(ids)
        return result

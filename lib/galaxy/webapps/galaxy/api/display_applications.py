"""
API operations on annotations.
"""

import logging
from typing import (
    Optional,
)

from fastapi import Body

from galaxy.managers.display_applications import (
    DisplayApplication,
    DisplayApplicationsManager,
    ReloadFeedback,
)
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["display_applications"])


@router.cbv
class FastAPIDisplay:
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

"""
API operations on annotations.
"""
import logging
from typing import (
    Dict,
    List,
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


@router.get(
    "/api/display_applications",
    summary="Returns the list of display applications.",
    name="display_applications_index",
)
def index(
    manager: DisplayApplicationsManager = depends(DisplayApplicationsManager),
) -> List[DisplayApplication]:
    """
    Returns the list of display applications.
    """
    return manager.index()


@router.post(
    "/api/display_applications/reload",
    summary="Reloads the list of display applications.",
    name="display_applications_reload",
    require_admin=True,
)
def reload(
    payload: Optional[Dict[str, List[str]]] = Body(default=None),
    manager: DisplayApplicationsManager = depends(DisplayApplicationsManager),
) -> ReloadFeedback:
    """
    Reloads the list of display applications.
    """
    payload = payload or {}
    ids = payload.get("ids", [])
    result = manager.reload(ids)
    return result

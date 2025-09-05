"""
API Controller providing Galaxy Tours
"""

import logging

from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.tours import ToursManager
from galaxy.schema.schema import GenerateTourResponse
from galaxy.tours import (
    TourDetails,
    TourList,
    ToursRegistry,
)
from galaxy.webapps.galaxy.api import DependsOnTrans
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)


router = Router(tags=["tours"])


@router.cbv
class FastAPITours:
    registry: ToursRegistry = depends(ToursRegistry)  # type: ignore[type-abstract]  # https://github.com/python/mypy/issues/4717
    manager: ToursManager = depends(ToursManager)

    @router.get("/api/tours", public=True)
    def index(self) -> TourList:
        """Return list of available tours."""
        return self.registry.get_tours()

    @router.get("/api/tours/generate", public=True)
    def generate_tour(
        self, tool_id: str, tool_version: str, trans: ProvidesAppContext = DependsOnTrans
    ) -> GenerateTourResponse:
        """Generate a tour designed for the given tool."""
        return self.manager.generate_tour(tool_id, tool_version, trans)

    @router.get("/api/tours/{tour_id}", public=True)
    def show(self, tour_id: str) -> TourDetails:
        """Return a tour definition."""
        return self.registry.tour_contents(tour_id)

    @router.post("/api/tours/{tour_id}", require_admin=True)
    def update_tour(self, tour_id: str) -> TourDetails:
        """Return a tour definition."""
        return self.registry.load_tour(tour_id)

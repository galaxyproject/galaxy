"""
API Controller providing Galaxy Tours
"""
import logging

from galaxy.tours import (
    TourDetails,
    TourList,
    ToursRegistry,
)
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)


router = Router(tags=["tours"])


@router.cbv
class FastAPITours:
    # ugh - mypy https://github.com/python/mypy/issues/5374
    registry: ToursRegistry = depends(ToursRegistry)  # type: ignore[type-abstract]

    @router.get("/api/tours")
    def index(self) -> TourList:
        """Return list of available tours."""
        return self.registry.get_tours()

    @router.get("/api/tours/{tour_id}")
    def show(self, tour_id: str) -> TourDetails:
        """Return a tour definition."""
        return self.registry.tour_contents(tour_id)

    @router.post("/api/tours/{tour_id}", require_admin=True)
    def update_tour(self, tour_id: str) -> TourDetails:
        """Return a tour definition."""
        return self.registry.load_tour(tour_id)

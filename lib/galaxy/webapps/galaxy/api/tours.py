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


@router.get("/api/tours")
def index(registry: ToursRegistry = depends(ToursRegistry)) -> TourList:  # type: ignore[type-abstract]  # https://github.com/python/mypy/issues/4717
    """Return list of available tours."""
    return registry.get_tours()


@router.get("/api/tours/{tour_id}")
def show(tour_id: str, registry: ToursRegistry = depends(ToursRegistry)) -> TourDetails:  # type: ignore[type-abstract]  # https://github.com/python/mypy/issues/4717
    """Return a tour definition."""
    return registry.tour_contents(tour_id)


@router.post("/api/tours/{tour_id}", require_admin=True)
def update_tour(tour_id: str, registry: ToursRegistry = depends(ToursRegistry)) -> TourDetails:  # type: ignore[type-abstract]  # https://github.com/python/mypy/issues/4717
    """Return a tour definition."""
    return registry.load_tour(tour_id)

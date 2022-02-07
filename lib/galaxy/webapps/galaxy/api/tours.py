"""
API Controller providing Galaxy Tours
"""
import logging

from galaxy.tours import (
    TourDetails,
    TourList,
    ToursRegistry,
)
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    require_admin,
)
from . import (
    BaseGalaxyAPIController,
    depends,
    Router,
)

log = logging.getLogger(__name__)


router = Router(tags=["tours"])


@router.cbv
class FastAPITours:
    # ugh - mypy https://github.com/python/mypy/issues/5374
    registry: ToursRegistry = depends(ToursRegistry)  # type: ignore[misc]

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


class ToursController(BaseGalaxyAPIController):
    registry: ToursRegistry = depends(ToursRegistry)  # type: ignore[misc]

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/tours/

        Displays available tours
        """
        return self.registry.get_tours()

    @expose_api_anonymous_and_sessionless
    def show(self, trans, tour_id, **kwd):
        """
        GET /api/tours/{tour_id}

        Read a YAML file containing the specified tour definition.

        :returns:   tour definition
        :rtype:     dictionary
        """
        return self.registry.tour_contents(tour_id)

    @require_admin
    @expose_api
    def update_tour(self, trans, tour_id, **kwd):
        """This simply reloads tours right now.  It's a quick hack."""
        # TODO: allow creation of new tours (which get written to the
        # filesystem).
        return self.registry.load_tour(tour_id)

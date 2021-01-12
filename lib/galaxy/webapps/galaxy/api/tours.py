"""
API Controller providing Galaxy Tours
"""
import logging

from fastapi import Depends
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter as APIRouter

from galaxy.tours import (
    TourDetails,
    TourList,
    ToursRegistry,
)
from galaxy.web import (
    expose_api_anonymous_and_sessionless,
    legacy_expose_api,
    require_admin
)
from galaxy.webapps.base.controller import BaseAPIController
from . import (
    get_admin_user,
    get_app,
)

log = logging.getLogger(__name__)


router = APIRouter(tags=['tours'])


def get_tours_registry(app=Depends(get_app)) -> ToursRegistry:
    return app.tour_registry


@cbv(router)
class FastAPITours:
    registry: ToursRegistry = Depends(get_tours_registry)

    @router.get('/api/tours')
    def index(self) -> TourList:
        """Return list of available tours."""
        return self.registry.tours_by_id_with_description()

    @router.get('/api/tours/{tour_id}')
    def show(self, tour_id: str) -> TourDetails:
        """Return a tour definition."""
        return self.registry.tour_contents(tour_id)

    @router.post('/api/tours/{tour_id}', dependencies=[Depends(get_admin_user)])
    def update_tour(self, tour_id: str) -> TourDetails:
        """Return a tour definition."""
        return self.registry.load_tour(tour_id)


class ToursController(BaseAPIController):

    def __init__(self, app):
        super().__init__(app)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        *GET /api/tours/
        Displays available tours
        """
        return self.app.tour_registry.tours_by_id_with_description()

    @expose_api_anonymous_and_sessionless
    def show(self, trans, tour_id, **kwd):
        """
        load_config( self, trans, Tour_config_file, **kwd )
        * GET /api/tours/{tour_id}:
            Read a yaml file containing the specified tour definition

        :returns:   tour definition
        :rtype:     dictionary
        """
        return self.app.tour_registry.tour_contents(tour_id)

    @require_admin
    @legacy_expose_api
    def update_tour(self, trans, tour_id, **kwd):
        """
        This simply reloads tours right now.  It's a quick hack.

        TODO: allow creation of new tours (which get written to the
        filesystem).
        """
        return self.app.tour_registry.load_tour(tour_id)

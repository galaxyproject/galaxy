"""
API Controller providing Galaxy Tours
"""
import logging

from galaxy.web import (
    _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless,
    expose_api,
    require_admin
)
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger( __name__ )


class ToursController( BaseAPIController ):

    def __init__( self, app ):
        super( ToursController, self ).__init__( app )

    @expose_api_anonymous_and_sessionless
    def index( self, trans, **kwd ):
        """
        *GET /api/tours/
        Displays available tours
        """
        return self.app.tour_registry.tours_by_id_with_description()

    @expose_api_anonymous_and_sessionless
    def show( self, trans, tour_id, **kwd ):
        """
        load_config( self, trans, Tour_config_file, **kwd )
        * GET /api/tours/{tour_id}:
            Read a yaml file containing the specified tour definition

        :returns:   tour definition
        :rtype:     dictionary
        """
        return self.app.tour_registry.tour_contents(tour_id)

    @expose_api
    @require_admin
    def update_tour( self, trans, tour_id, **kwd ):
        """
        This simply reloads tours right now.  It's a quick hack.

        TODO: allow creation of new tours (which get written to the
        filesystem).
        """
        return self.app.tour_registry.load_tour(tour_id)

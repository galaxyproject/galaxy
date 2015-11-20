"""
API Controller providing Galaxy Tours
"""
import logging
from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
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
        return trans.app.tour_registry.tours_by_id_with_description()

    @expose_api_anonymous_and_sessionless
    def show( self, trans, tour_id, **kwd ):
        """
        load_config( self, trans, Tour_config_file, **kwd )
        * GET /api/tours/{tour_config_file}:
            Read a yaml file containing the specified tour definition

        :returns:   tour definition
        :rtype:     dictionary
        """
        return trans.app.tour_registry.tour_contents(tour_id)

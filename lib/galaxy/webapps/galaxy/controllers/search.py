
"""
Contains a basic search interface for Galaxy
"""
import logging
from galaxy import web
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger( __name__ )

class SearchController( BaseUIController ):
    @web.expose
    def index(self, trans):
        return trans.fill_template( "search/index.mako")

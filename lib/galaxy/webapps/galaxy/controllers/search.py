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
        """
        Per the message, this is not ready for human consumption, yet.  Power
        users can still use the search API.
        """
        return trans.show_message("Sorry, the search interface isn't quite ready for use, yet.  Watch the release notes and check back later!")

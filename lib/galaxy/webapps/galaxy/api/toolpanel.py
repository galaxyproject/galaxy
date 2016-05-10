"""
API operations on Galaxy's toolpanel.
"""
import logging
from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger( __name__ )


class ToolpanelController( BaseAPIController ):

    def __init__( self, app ):
        super( ToolpanelController, self ).__init__( app )

    @expose_api_anonymous_and_sessionless
    def index( self, trans, **kwd ):
        """
        * GET /api/toolpanel:
            Return a list of sections in the toolpanel.

        :returns:   list of toolpanel sections
        :rtype:     list

        """
        sections = [ dict( id=section[0], name=section[1] ) for section in trans.app.toolbox.get_sections() ]
        return sections

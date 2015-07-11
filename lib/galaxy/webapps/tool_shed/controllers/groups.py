import logging
from galaxy import model, util
from galaxy import web
from galaxy.model.orm import and_, not_, or_
from galaxy.web.base.controller import BaseUIController
from galaxy.web.framework.helpers import escape, grids

log = logging.getLogger( __name__ )


class Group( BaseUIController ):

    @web.expose
    def index( self, trans, **kwd ):
        # define app configuration for generic mako template
        app = {
            'jscript'       : "../toolshed/scripts/toolshed.groups"
        }
        return trans.fill_template( '/webapps/tool_shed/group/index.mako',
                                    config = { 
                                    'title': 'Tool Shed Groups',
                                    'app': app } )

import logging
from galaxy import web
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger( __name__ )


class AdminBeta( BaseUIController ):

    @web.expose
    @web.require_admin
    def index( self, trans, **kwd ):
        # define app configuration for generic mako template
        app = {
            'jscript': "galaxy.admin"
        }
        return trans.fill_template( 'galaxy.panels.mako',
                                    config={
                                        'title': 'Galaxy Admin',
                                        'app': app } )

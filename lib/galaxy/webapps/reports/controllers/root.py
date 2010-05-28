from galaxy.web.base.controller import *
import logging
log = logging.getLogger( __name__ )

class Report( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        return trans.fill_template( '/webapps/reports/index.mako' )

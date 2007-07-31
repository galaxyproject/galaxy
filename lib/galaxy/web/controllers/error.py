from galaxy.web.base.controller import *

class Error( BaseController ):
    @web.expose
    def index( self, trans ):
        raise Exception, "Fake error"
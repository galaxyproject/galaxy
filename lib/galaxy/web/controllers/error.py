from galaxy.web.base.controller import *

class Error( BaseUIController ):
    @web.expose
    def index( self, trans ):
        raise Exception, "Fake error"
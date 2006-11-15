import common
from galaxy import web

class Error( common.Root ):
    @web.expose
    def index( self, trans ):
        raise Exception, "Fake error"
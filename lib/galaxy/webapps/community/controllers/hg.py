import os, logging
from galaxy.web.base.controller import *
from mercurial.hgweb.hgwebdir_mod import hgwebdir
from mercurial.hgweb.request import wsgiapplication

log = logging.getLogger(__name__)

class HgController( BaseController ):
    @web.expose
    def handle_request( self, trans, **kwd ):
        # The os command that results in this method being called will look something like
        # hg clone http://test@127.0.0.1:9009/repos/test/convert_characters1
        return wsgiapplication( make_web_app )                     

def make_web_app():
    hgweb_config = "%s/hgweb.config" %  os.getcwd()
    if not os.path.exists( hgweb_config ):
        raise Exception( "Required file hgweb.config does not exist in directory %s" % os.getcwd() )
    hgwebapp = hgwebdir( hgweb_config )
    return hgwebapp

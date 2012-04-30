import os, logging
from galaxy.web.base.controller import *
from galaxy.webapps.community.controllers.common import *

from galaxy import eggs
eggs.require('mercurial')
from mercurial.hgweb.hgwebdir_mod import hgwebdir
from mercurial.hgweb.request import wsgiapplication

log = logging.getLogger(__name__)

class HgController( BaseUIController ):
    @web.expose
    def handle_request( self, trans, **kwd ):
        # The os command that results in this method being called will look something like
        # hg clone http://test@127.0.0.1:9009/repos/test/convert_characters1
        cmd = kwd.get( 'cmd', None )
        wsgi_app = wsgiapplication( make_web_app )
        # Hack: Add a parameter to requests for which we do not want all repository metadata reset.
        reset_metadata = not ( kwd.get( 'no_reset', False ) )
        if cmd == 'listkeys' and reset_metadata:
            # This possibly results from an "hg push" from the command line.  When doing this, the following 7 commands, in order,
            # will be retrieved from environ: between -> capabilities -> heads -> branchmap -> unbundle -> unbundle -> listkeys
            path_info = kwd.get( 'path_info', None )
            if path_info:
                owner, name = path_info.split( '/' )
                repository = get_repository_by_name_and_owner( trans, name, owner )
                if repository:
                    reset_all_repository_metadata( trans, trans.security.encode_id( repository.id ) )
        return wsgi_app

def make_web_app():
    hgweb_config = "%s/hgweb.config" %  os.getcwd()
    if not os.path.exists( hgweb_config ):
        raise Exception( "Required file hgweb.config does not exist in directory %s" % os.getcwd() )
    hgwebapp = hgwebdir( hgweb_config )
    return hgwebapp

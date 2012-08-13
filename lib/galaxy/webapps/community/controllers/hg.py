import os, logging
from galaxy.web.base.controller import *
from galaxy.webapps.community.controllers.common import *
from galaxy.util.shed_util import update_repository

from galaxy import eggs
eggs.require('mercurial')
import mercurial.__version__
from mercurial.hgweb.hgwebdir_mod import hgwebdir
from mercurial.hgweb.request import wsgiapplication

log = logging.getLogger(__name__)

class HgController( BaseUIController ):
    @web.expose
    def handle_request( self, trans, **kwd ):
        # The os command that results in this method being called will look something like
        # hg clone http://test@127.0.0.1:9009/repos/test/convert_characters1
        hg_version = mercurial.__version__.version
        cmd = kwd.get( 'cmd', None )
        wsgi_app = wsgiapplication( make_web_app )
        if hg_version >= '2.2.3' and cmd == 'pushkey':                
            # When doing an "hg push" from the command line, the following commands, in order, will be retrieved from environ, depending
            # upon the mercurial version being used.  In mercurial version 2.2.3, section 15.2. Command changes includes a new feature: 
            # pushkey: add hooks for pushkey/listkeys (see http://mercurial.selenic.com/wiki/WhatsNew#Mercurial_2.2.3_.282012-07-01.29).
            # We require version 2.2.3 since the pushkey hook was added in that version.
            # If mercurial version >= '2.2.3': capabilities -> batch -> branchmap -> unbundle -> listkeys -> pushkey
            path_info = kwd.get( 'path_info', None )
            if path_info:
                owner, name = path_info.split( '/' )
                repository = get_repository_by_name_and_owner( trans, name, owner )
                if repository:
                    if hg_version >= '2.2.3':
                        # Set metadata using the repository files on disk.
                        error_message, status = set_repository_metadata( trans, repository )
                        if status not in [ 'ok' ] and error_message:
                            log.debug( "Error resetting metadata on repository '%s': %s" % ( str( repository.name ), str( error_message ) ) )
                        elif status in [ 'ok' ] and error_message:
                            log.debug( "Successfully reset metadata on repository %s, but encountered problem: %s" % ( str( repository.name ), str( error_message ) ) )
        return wsgi_app

def make_web_app():
    hgweb_config = "%s/hgweb.config" %  os.getcwd()
    if not os.path.exists( hgweb_config ):
        raise Exception( "Required file hgweb.config does not exist in directory %s" % os.getcwd() )
    hgwebapp = hgwebdir( hgweb_config )
    return hgwebapp
